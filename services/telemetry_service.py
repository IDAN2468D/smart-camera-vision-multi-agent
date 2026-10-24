import time
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TelemetryCostService:
    """Context Engineering, Token Accounting, and Performance Analytics Service.
    
    Implements core syllabus concepts (Pages 15, 16, 18):
    - Token Accounting (Prompt vs Completion tokens)
    - Latency Tracking (ms) across multi-agent steps
    - Cost Estimation (USD / ILS)
    - Context Window monitoring
    """

    # Gemini 3.5 Flash Lite pricing (approx $0.075 / 1M input, $0.30 / 1M output)
    COST_PER_1M_INPUT = 0.075
    COST_PER_1M_OUTPUT = 0.30
    USD_TO_ILS = 3.70

    def __init__(self):
        self._lock = threading.Lock()
        self.total_scans = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_latency_seconds = 0.0
        self.total_human_evaluations = 0

    def extract_tokens_from_response(self, response: Any) -> tuple:
        """Extract prompt and completion tokens from model response if available."""
        prompt_tokens = 450
        completion_tokens = 180
        try:
            if hasattr(response, "metrics") and response.metrics:
                prompt_tokens = getattr(response.metrics, "prompt_tokens", prompt_tokens) or prompt_tokens
                completion_tokens = getattr(response.metrics, "completion_tokens", completion_tokens) or completion_tokens
            elif hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", prompt_tokens) or prompt_tokens
                completion_tokens = getattr(response.usage, "completion_tokens", completion_tokens) or completion_tokens
        except Exception:
            pass
        return prompt_tokens, completion_tokens

    def record_scan_metrics(
        self,
        duration_seconds: float,
        prompt_tokens: int = 450,
        completion_tokens: int = 180
    ):
        """Record telemetry for an executed multi-agent scan."""
        with self._lock:
            self.total_scans += 1
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_latency_seconds += duration_seconds

    def record_human_eval(self):
        """Record an HITL user evaluation."""
        with self._lock:
            self.total_human_evaluations += 1

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculate and return aggregated telemetry metrics."""
        with self._lock:
            scans = max(self.total_scans, 1)
            avg_latency = (self.total_latency_seconds / scans) if self.total_scans > 0 else 0.0

            # Calculate total cost in USD
            input_cost = (self.total_prompt_tokens / 1_000_000) * self.COST_PER_1M_INPUT
            output_cost = (self.total_completion_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT
            total_usd = input_cost + output_cost
            total_ils = total_usd * self.USD_TO_ILS

            return {
                "total_scans": self.total_scans,
                "avg_latency_ms": round(avg_latency * 1000),
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "estimated_cost_usd": f"${total_usd:.5f}",
                "estimated_cost_ils": f"₪{total_ils:.4f}",
                "cost_per_scan_ils": f"₪{(total_ils / scans):.4f}" if self.total_scans > 0 else "₪0.0000",
                "human_evaluations_count": self.total_human_evaluations
            }

# Singleton service instance
telemetry_service = TelemetryCostService()
