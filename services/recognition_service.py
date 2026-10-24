import time
import logging
from typing import Optional
from models.detection_schema import DetectionRecord
from dal.detection_repo import detection_repo, DetectionRepository
from services.sse_service import sse_service
from services.guardrails_service import guardrails_service
from services.telemetry_service import telemetry_service

logger = logging.getLogger(__name__)

class RecognitionService:
    """Business Logic Layer coordinating Orchestrator processing, Guardrails, Telemetry, DAL, and SSE."""

    def __init__(self, repo: Optional[DetectionRepository] = None):
        self.repo = repo or detection_repo
        self._orchestrator = None

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            from agents.orchestrator_team import orchestrator_team
            self._orchestrator = orchestrator_team
        return self._orchestrator

    def analyze_and_store(
        self,
        frame_path: str,
        trigger_source: str = "manual_space",
        gesture_detected: Optional[str] = None
    ) -> DetectionRecord:
        """Run multi-agent recognition pipeline, apply guardrails, record telemetry, and persist to MongoDB.
        
        Args:
            frame_path: Path to the saved image frame.
            trigger_source: Origin of trigger (e.g. manual_space, gesture_thumbs_up, web_hud).
            gesture_detected: Recognized gesture if any.
            
        Returns:
            The complete DetectionRecord including vision output, enrichment, pricing, and audio.
        """
        start_time = time.time()
        logger.info(f"Initiating multi-agent recognition pipeline for frame: {frame_path} (source: {trigger_source})")
        
        # 1. Process frame with multi-agent orchestrator
        record: DetectionRecord = self.orchestrator.process_camera_frame(
            frame_path,
            trigger_source=trigger_source,
            gesture_detected=gesture_detected
        )

        duration = time.time() - start_time

        # 2. Apply AI Guardrails & PII Sanitization
        guardrail_result = guardrails_service.apply_guardrails(record)
        logger.info(f"[Guardrails] Evaluation completed: safe={guardrail_result['is_safe']}, passed={guardrail_result['passed']}")

        # 3. Record Token Accounting & Latency Telemetry
        telemetry_service.record_scan_metrics(duration_seconds=duration)
        
        # 4. Persist record to MongoDB Atlas
        try:
            doc_id = self.repo.save_detection(record)
            logger.info(f"Detection successfully stored in MongoDB with ID: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to persist detection record to MongoDB: {e}")
            
        # 5. Broadcast real-time SSE event to all connected web clients
        try:
            sse_service.publish("new_detection", record.model_dump(mode="json", exclude={"image_embedding"}))
        except Exception as e:
            logger.error(f"Failed to broadcast SSE new_detection event: {e}")

        return record

# Singleton service instance
recognition_service = RecognitionService()
