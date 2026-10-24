import time
import logging
from typing import Dict, Any, List, Optional
from models.detection_schema import SceneDeltaReport, VisionAnalysisResult

logger = logging.getLogger(__name__)

class SceneDiffService:
    """Temporal comparison service tracking object appearance, departures, and dwell times."""

    def __init__(self):
        # Maps zone_name -> {"entities": set(), "timestamp": float, "last_object": str}
        self._zone_states: Dict[str, Dict[str, Any]] = {}

    def compute_delta(
        self,
        vision_result: VisionAnalysisResult,
        zone_id: str = "default_zone"
    ) -> SceneDeltaReport:
        now = time.time()
        current_entities = set(vision_result.detected_entities)
        if vision_result.object_name:
            current_entities.add(vision_result.object_name)

        prev_state = self._zone_states.get(zone_id)

        if not prev_state:
            # First time this zone/scene is observed
            self._zone_states[zone_id] = {
                "entities": current_entities,
                "timestamp": now,
                "last_object": vision_result.object_name
            }
            return SceneDeltaReport(
                added_entities=list(current_entities),
                removed_entities=[],
                dwell_time_seconds=0,
                delta_summary_hebrew="מצב התחלתי של האזור נקלט בהצלחה."
            )

        prev_entities = prev_state.get("entities", set())
        prev_time = prev_state.get("timestamp", now)
        dwell_time = int(now - prev_time)

        added = list(current_entities - prev_entities)
        removed = list(prev_entities - current_entities)

        # Update state
        self._zone_states[zone_id] = {
            "entities": current_entities,
            "timestamp": now,
            "last_object": vision_result.object_name
        }

        # Build concise Hebrew summary
        summary_parts = []
        if added:
            summary_parts.append(f"נוספו לסצנה: {', '.join(added)}")
        if removed:
            summary_parts.append(f"נלקחו/נעלמו: {', '.join(removed)}")
        if not added and not removed:
            summary_parts.append(f"ללא שינוי בסצנה (שהייה של {dwell_time} שניות).")

        return SceneDeltaReport(
            added_entities=added,
            removed_entities=removed,
            dwell_time_seconds=dwell_time,
            delta_summary_hebrew="; ".join(summary_parts)
        )

# Singleton service instance
scene_diff_service = SceneDiffService()
