import time
import logging
from typing import Optional
from models.detection_schema import DetectionRecord, VisionAnalysisResult, ProductPriceInfo
from agents.vision_agent import vision_agent, VisionPerceptionAgent
from agents.knowledge_agent import knowledge_agent, KnowledgeEnrichmentAgent
from agents.commerce_agent import commerce_agent, CommercePriceAgent
from services.thumbnail_service import thumbnail_service, ThumbnailService
from services.voice_service import voice_service, VoiceService
from services.sse_service import sse_service

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """Orchestrator coordinating Vision, Knowledge, Commerce, and Voice AI Agents."""

    def __init__(
        self,
        vision: Optional[VisionPerceptionAgent] = None,
        knowledge: Optional[KnowledgeEnrichmentAgent] = None,
        commerce: Optional[CommercePriceAgent] = None,
        voice: Optional[VoiceService] = None,
        thumbnail: Optional[ThumbnailService] = None
    ):
        self.vision_agent = vision or vision_agent
        self.knowledge_agent = knowledge or knowledge_agent
        self.commerce_agent = commerce or commerce_agent
        self.voice_service = voice or voice_service
        self.thumbnail_service = thumbnail or thumbnail_service

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

        # Step 0: Generate Lightweight WebP Thumbnail
        thumbnail_b64 = self.thumbnail_service.create_webp_thumbnail(image_path)

        # Step 1: Vision Perception (Gemini 3.5 Flash Lite Vision + OCR)
        step1_start = time.time()
        vision_result: VisionAnalysisResult = self.vision_agent.analyze_frame(image_path)
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

        # Step 2: Knowledge & Memory Enrichment (MongoDB Tool + Gemini Reasoning)
        step2_start = time.time()
        enrichment_summary: str = self.knowledge_agent.enrich(vision_result)
        logger.info(
            f"[Orchestrator] Step 2 (Knowledge) completed in {time.time() - step2_start:.2f}s"
        )
        sse_service.publish("pipeline_status", {"status": "step_completed", "step": "knowledge"})

        # Step 3: Commerce & Pricing Agent (if commercial gadget or item)
        product_info: Optional[ProductPriceInfo] = None
        if self.commerce_agent.is_commercial_item(vision_result):
            step3_start = time.time()
            sse_service.publish("pipeline_status", {"status": "step_started", "step": "commerce"})
            product_info = self.commerce_agent.lookup_product(vision_result)
            logger.info(
                f"[Orchestrator] Step 3 (Commerce) completed in {time.time() - step3_start:.2f}s: "
                f"Model={product_info.model_name if product_info else 'N/A'}"
            )
            sse_service.publish("pipeline_status", {"status": "step_completed", "step": "commerce"})

        # Step 4: Hebrew Voice Agent (TTS synthesis)
        step4_start = time.time()
        sse_service.publish("pipeline_status", {"status": "step_started", "step": "voice"})
        # Synthesize audio from the Hebrew enrichment summary
        tts_audio_base64 = self.voice_service.generate_speech(enrichment_summary)
        logger.info(
            f"[Orchestrator] Step 4 (Voice TTS) completed in {time.time() - step4_start:.2f}s"
        )

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
            tts_audio_base64=tts_audio_base64
        )

        total_duration = time.time() - start_time
        logger.info(f"[Orchestrator] Complete v2.0 pipeline finished in {total_duration:.2f}s for '{record.object_name}'")
        return record

# Singleton orchestrator instance
orchestrator_team = MultiAgentOrchestrator()
