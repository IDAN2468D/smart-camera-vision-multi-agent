import time
import logging
import concurrent.futures
from typing import Optional, List, Dict, Any
from models.detection_schema import DetectionRecord, VisionAnalysisResult, ProductPriceInfo
from agents.vision_agent import vision_agent, VisionPerceptionAgent
from agents.knowledge_agent import knowledge_agent, KnowledgeEnrichmentAgent
from agents.commerce_agent import commerce_agent, CommercePriceAgent
from services.thumbnail_service import thumbnail_service, ThumbnailService
from services.voice_service import voice_service, VoiceService
from services.embedding_client import embedding_client, EmbeddingClient
from services.sse_service import sse_service
from dal.detection_repo import detection_repo
from config.settings import settings

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """Orchestrator coordinating Vision, Knowledge, Commerce, and Voice AI Agents."""

    def __init__(
        self,
        vision: Optional[VisionPerceptionAgent] = None,
        knowledge: Optional[KnowledgeEnrichmentAgent] = None,
        commerce: Optional[CommercePriceAgent] = None,
        voice: Optional[VoiceService] = None,
        thumbnail: Optional[ThumbnailService] = None,
        embeddings: Optional[EmbeddingClient] = None
    ):
        self.vision_agent = vision or vision_agent
        self.knowledge_agent = knowledge or knowledge_agent
        self.commerce_agent = commerce or commerce_agent
        self.voice_service = voice or voice_service
        self.thumbnail_service = thumbnail or thumbnail_service
        self.embedding_client = embeddings or embedding_client

    def process_camera_frame(
        self,
        image_path: str,
        trigger_source: str = "manual_space",
        gesture_detected: Optional[str] = None
    ) -> DetectionRecord:
        """Run the end-to-end multi-agent perception, pricing, and voice synthesis pipeline.
        
        Args:
            image_path: Path to the camera frame file.
            trigger_source: Origin of trigger (e.g. 'manual_space', 'gesture_thumbs_up', 'web_hud').
            gesture_detected: Any specific gesture detected ('thumbs_up', 'open_palm', None).
            
        Returns:
            Fully enriched DetectionRecord.
        """
        start_time = time.time()
        logger.info(f"[Orchestrator] Starting multi-agent pipeline for frame: {image_path} (trigger: {trigger_source})")
        sse_service.publish("pipeline_status", {"status": "started", "step": "vision", "trigger": trigger_source})

        # Step 0 & 1: Parallel Perception (Thumbnail + Gemini 3.5 Vision Perception)
        step1_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pre_executor:
            future_thumb = pre_executor.submit(self.thumbnail_service.create_webp_thumbnail, image_path)
            vision_result: VisionAnalysisResult = self.vision_agent.analyze_frame(image_path)
            thumbnail_b64 = future_thumb.result()

        logger.info(
            f"[Orchestrator] Step 1 (Vision) completed in {time.time() - step1_start:.2f}s: "
            f"Object='{vision_result.object_name}', Conf={vision_result.confidence:.2f}"
        )
        sse_service.publish("pipeline_status", {
            "status": "step_completed",
            "step": "vision",
            "object_name": vision_result.object_name,
            "confidence": vision_result.confidence
        })

        # Step 2 & 3: Concurrent Multi-Agent Execution (Commerce + Embedding + Knowledge RAG)
        # Commerce lookup and History pre-fetching run in parallel with Embedding & Vector Search
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Branch A: Commerce & Pricing Agent (runs asynchronously in background thread)
            future_commerce = None
            if self.commerce_agent.is_commercial_item(vision_result):
                sse_service.publish("pipeline_status", {"status": "step_started", "step": "commerce"})
                future_commerce = executor.submit(self.commerce_agent.lookup_product, vision_result)

            # Branch B: Pre-fetch historical detections from MongoDB in parallel (fast, ~15ms)
            future_history = executor.submit(detection_repo.find_by_object_name, vision_result.object_name, 3)

            # Branch C: Multimodal Visual RAG Embedding
            step15_start = time.time()
            sse_service.publish("pipeline_status", {"status": "step_started", "step": "embedding"})
            image_embedding: Optional[List[float]] = None
            embedding_model: Optional[str] = None
            similar_items: List[Dict[str, Any]] = []

            try:
                embedding = self.embedding_client.embed_frame(image_path, vision_result)
                if embedding:
                    image_embedding = embedding["embedding"]
                    embedding_model = embedding["model"]
                    search = self.embedding_client.search_similar(
                        vector=image_embedding,
                        model=embedding_model,
                        limit=3,
                        min_score=settings.SIMILARITY_THRESHOLD
                    )
                    similar_items = search.get("data", [])
            except Exception as e:
                logger.warning(f"[Orchestrator] Step 1.5 (Embedding) failed, continuing without Visual RAG: {e}")

            logger.info(
                f"[Orchestrator] Step 1.5 (Embedding) completed in {time.time() - step15_start:.2f}s: "
                f"model={embedding_model}, similar_items={len(similar_items)}"
            )
            sse_service.publish("pipeline_status", {
                "status": "step_completed",
                "step": "embedding",
                "similar_items": [
                    {"object_name": s.get("object_name"), "score": round(s.get("similarity_score", 0.0), 3)}
                    for s in similar_items
                ]
            })

            # Retrieve pre-fetched MongoDB history (already finished in parallel)
            history = future_history.result()

            # Step 2: Knowledge & Memory Enrichment (Single-shot inference with injected history & RAG)
            step2_start = time.time()
            sse_service.publish("pipeline_status", {"status": "step_started", "step": "knowledge"})
            enrichment_summary: str = self.knowledge_agent.enrich(
                vision_result,
                similar_items=similar_items,
                history=history
            )
            logger.info(
                f"[Orchestrator] Step 2 (Knowledge) completed in {time.time() - step2_start:.2f}s"
            )
            sse_service.publish("pipeline_status", {"status": "step_completed", "step": "knowledge"})

            # Step 4: Hebrew Voice Agent (TTS synthesis runs immediately while collecting Commerce)
            step4_start = time.time()
            sse_service.publish("pipeline_status", {"status": "step_started", "step": "voice"})
            future_voice = executor.submit(self.voice_service.generate_speech, enrichment_summary)

            # Collect Commerce results (was running in parallel since Step 1, zero added latency)
            product_info: Optional[ProductPriceInfo] = None
            if future_commerce:
                try:
                    product_info = future_commerce.result()
                    logger.info(
                        f"[Orchestrator] Step 3 (Commerce) completed in parallel: "
                        f"Model={product_info.model_name if product_info else 'N/A'}"
                    )
                except Exception as e:
                    logger.warning(f"[Orchestrator] Commerce lookup in parallel failed: {e}")
                sse_service.publish("pipeline_status", {"status": "step_completed", "step": "commerce"})

            # Collect Voice TTS results
            tts_audio_base64: Optional[str] = None
            try:
                tts_audio_base64 = future_voice.result()
            except Exception as e:
                logger.warning(f"[Orchestrator] Voice TTS in parallel failed: {e}")

            logger.info(
                f"[Orchestrator] Step 4 (Voice TTS) completed in {time.time() - step4_start:.2f}s"
            )
            sse_service.publish("pipeline_status", {"status": "step_completed", "step": "voice"})

        # Step 5: Synthesis into validated DetectionRecord
        record = DetectionRecord(
            object_name=vision_result.object_name,
            category=vision_result.category,
            detected_entities=vision_result.detected_entities,
            face_detected=vision_result.face_detected,
            hands_detected=vision_result.hands_detected,
            detected_text=vision_result.detected_text,
            confidence=vision_result.confidence,
            visual_description=vision_result.visual_description,
            enrichment_summary=enrichment_summary,
            trigger_source=trigger_source,
            gesture_detected=gesture_detected,
            product_info=product_info,
            thumbnail_base64=thumbnail_b64,
            tts_audio_base64=tts_audio_base64,
            image_embedding=image_embedding,
            embedding_model=embedding_model
        )

        total_duration = time.time() - start_time
        logger.info(f"[Orchestrator] Complete v2.0 pipeline finished in {total_duration:.2f}s for '{record.object_name}'")
        return record

# Singleton orchestrator instance
orchestrator_team = MultiAgentOrchestrator()
