import re
import logging
from typing import Dict, Any, Optional
from models.detection_schema import DetectionRecord, VisionAnalysisResult

logger = logging.getLogger(__name__)

class AgentGuardrailsService:
    """Enterprise AI Guardrails, Content Safety, and Human-In-The-Loop (HITL) Evaluation Service.
    
    Implements core concepts from the syllabus:
    - AI Guardrails & Hallucination Mitigation
    - PII Privacy Redaction (Phone, ID, Sensitive data in OCR)
    - Output Validation & Confidence Gating
    - Human-In-The-Loop Verification
    """

    MIN_CONFIDENCE_THRESHOLD = 0.60

    def apply_guardrails(self, record: DetectionRecord) -> Dict[str, Any]:
        """Validate, sanitize, and evaluate detection output before publishing.
        
        Returns:
            Dict containing guardrail status, flags, and sanitized fields.
        """
        flags = []
        is_safe = True

        # 1. Confidence Gating
        if record.confidence < self.MIN_CONFIDENCE_THRESHOLD:
            flags.append("low_confidence_warning")
            logger.warning(
                f"[Guardrails] Confidence ({record.confidence:.2f}) below threshold ({self.MIN_CONFIDENCE_THRESHOLD}). Flagged for review."
            )

        # 2. Privacy & PII Redaction in OCR Text
        sanitized_ocr = record.detected_text
        if sanitized_ocr:
            # Redact Israeli phone numbers
            sanitized_ocr = re.sub(r'(\b05[0-9]-?[0-9]{7}\b)', '[REDACTED_PHONE]', sanitized_ocr)
            # Redact email addresses
            sanitized_ocr = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', sanitized_ocr)
            # Redact credit card patterns (16 digits)
            sanitized_ocr = re.sub(r'\b(?:\d{4}[ -]?){3}\d{4}\b', '[REDACTED_CARD]', sanitized_ocr)
            if sanitized_ocr != record.detected_text:
                flags.append("pii_redacted")
                record.detected_text = sanitized_ocr

        # 3. Content Safety Check
        banned_terms = {"weapon", "gun", "knife", "explosive", "narcotic"}
        for entity in record.detected_entities:
            if entity.lower() in banned_terms:
                flags.append("sensitive_entity_detected")
                is_safe = False

        return {
            "is_safe": is_safe,
            "passed": len(flags) == 0,
            "flags": flags,
            "human_verification_required": record.confidence < self.MIN_CONFIDENCE_THRESHOLD,
            "sanitized_ocr": record.detected_text
        }

    def record_human_feedback(
        self,
        db_collection,
        timestamp_iso: str,
        is_accurate: bool,
        corrected_label: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Store Human-In-The-Loop evaluation feedback in MongoDB Atlas."""
        try:
            update_data = {
                "human_evaluated": True,
                "human_verified": is_accurate,
                "evaluation_notes": notes,
                "corrected_label": corrected_label
            }
            # Match either ISO string or datetime object
            query = {"$or": [{"timestamp": timestamp_iso}]}
            try:
                from datetime import datetime
                query["$or"].append({"timestamp": datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))})
            except Exception:
                pass

            result = db_collection.update_one(query, {"$set": update_data})
            logger.info(f"[HITL] Human feedback recorded for detection {timestamp_iso}: verified={is_accurate}")
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            logger.error(f"[HITL] Failed to record feedback: {e}")
            return False

    def get_few_shot_corrections(self, db_collection, limit: int = 3) -> str:
        """Fetch verified human corrections to inject into agent prompt as few-shot examples."""
        try:
            cursor = db_collection.find(
                {"human_evaluated": True, "corrected_label": {"$exists": True, "$ne": None, "$ne": ""}},
                {"_id": 0, "object_name": 1, "corrected_label": 1, "visual_description": 1}
            ).limit(limit)
            corrections = list(cursor)
            if not corrections:
                return ""
            examples = []
            for c in corrections:
                examples.append(
                    f"- When observing '{c.get('visual_description', '')[:60]}', initial was '{c.get('object_name')}', but human verified it is '{c.get('corrected_label')}'."
                )
            return "\n".join(examples)
        except Exception as e:
            logger.debug(f"[HITL] Could not fetch few-shot corrections: {e}")
            return ""

# Singleton service instance
guardrails_service = AgentGuardrailsService()
