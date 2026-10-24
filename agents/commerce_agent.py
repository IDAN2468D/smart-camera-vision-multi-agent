import json
import logging
from typing import Optional
from agno.agent import Agent
from agno.models.google import Gemini
from config.settings import settings
from models.detection_schema import VisionAnalysisResult, ProductPriceInfo

logger = logging.getLogger(__name__)

NON_COMMERCIAL_CATEGORIES = {
    "human", "person", "face", "anatomy", "hands", "gesture", "anatomy/hands", "nature", "animal", "body"
}

NON_COMMERCIAL_OBJECTS = {
    "human face", "face", "hand", "right hand", "left hand", "palm", "open palm", "thumbs up", "person", "wall", "ceiling"
}

class CommercePriceAgent:
    """Agent 3: Market intelligence agent estimating product specs and price ranges in ILS (₪)."""

    def __init__(self, model_id: Optional[str] = None, api_key: Optional[str] = None):
        self.model_id = model_id or settings.MODEL_ID
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._agent = None
        self._cache: dict = {}

    def _get_agent(self) -> Agent:
        """Lazily initialize the Agno Agent with Gemini model for structured product pricing."""
        if self._agent is None:
            model = Gemini(
                id=self.model_id,
                api_key=self.api_key if self.api_key else None
            )

            instructions = [
                "You are an expert Israeli E-Commerce, Consumer Electronics & Gadget Valuation Specialist.",
                "Your role is to evaluate detected physical items and provide accurate market price estimations in Israel New Shekels (ILS / ₪) and concise technical specifications in Hebrew.",
                "Guidelines:",
                "1. If OCR text or brand names are visible, use them to identify the exact or most probable model (e.g., iPhone 15 Pro, Logitech MX Master 3S, Sony WH-1000XM5).",
                "2. Provide an estimated price range in Israel in ILS (₪) formatted like '₪1,200 - ₪1,500' or '₪350 - ₪420'.",
                "3. In specs_summary, provide 2-3 key technical highlights in clean, professional Hebrew.",
                "4. Output strictly according to the ProductPriceInfo schema."
            ]

            kwargs = {
                "name": "CommercePriceAgent",
                "model": model,
                "fallback_models": [
                    Gemini(id="gemini-3.5-flash", api_key=self.api_key if self.api_key else None),
                    Gemini(id="gemini-3.8-flash", api_key=self.api_key if self.api_key else None)
                ],
                "instructions": instructions,
                "markdown": False
            }

            if "output_schema" in Agent.__init__.__code__.co_varnames:
                kwargs["output_schema"] = ProductPriceInfo
            elif "response_model" in Agent.__init__.__code__.co_varnames:
                kwargs["response_model"] = ProductPriceInfo

            self._agent = Agent(**kwargs)
        return self._agent

    def is_commercial_item(self, vision_result: VisionAnalysisResult) -> bool:
        """Determine if a vision result represents a commercial product worth looking up."""
        cat = (vision_result.category or "").strip().lower()
        obj = (vision_result.object_name or "").strip().lower()

        if cat in NON_COMMERCIAL_CATEGORIES or obj in NON_COMMERCIAL_OBJECTS:
            return False

        # If detected entities contain commercial gadgets or items
        commercial_keywords = [
            "phone", "smartphone", "laptop", "watch", "mouse", "keyboard", "headphone",
            "earphone", "cup", "mug", "bottle", "pen", "device", "gadget", "electronics",
            "monitor", "camera", "tablet", "charger", "cable", "glasses", "sneakers", "book"
        ]

        if any(kw in obj or kw in cat for kw in commercial_keywords):
            return True

        for entity in vision_result.detected_entities:
            e_lower = entity.lower()
            if any(kw in e_lower for kw in commercial_keywords):
                return True

        return False

    def lookup_product(self, vision_result: VisionAnalysisResult) -> Optional[ProductPriceInfo]:
        """Perform pricing and technical lookup for a detected commercial item.
        
        Args:
            vision_result: Visual analysis details of the detected item.
            
        Returns:
            ProductPriceInfo instance or None if not applicable / failed.
        """
        if not self.is_commercial_item(vision_result):
            logger.debug(f"Item '{vision_result.object_name}' is not classified as commercial product. Skipping price lookup.")
            return None

        cache_key = f"{vision_result.object_name.lower().strip()}_{str(vision_result.detected_text).lower().strip()}"
        if cache_key in self._cache:
            logger.info(f"[CommerceAgent] Returning cached pricing for: '{vision_result.object_name}' (0ms)")
            return self._cache[cache_key]

        prompt = (
            f"Analyze this detected product and provide market price in ILS and specs in Hebrew:\n"
            f"- Object Name: {vision_result.object_name}\n"
            f"- Category: {vision_result.category}\n"
            f"- Detected Entities: {', '.join(vision_result.detected_entities)}\n"
            f"- Visible Text/Brands (OCR): {vision_result.detected_text or 'None'}\n"
            f"- Visual Details: {vision_result.visual_description}\n"
        )

        try:
            agent = self._get_agent()
            response = agent.run(prompt)
            content = response.content

            info: Optional[ProductPriceInfo] = None
            if isinstance(content, ProductPriceInfo):
                info = content
            elif isinstance(content, dict):
                info = ProductPriceInfo(**content)
            elif isinstance(content, str):
                # Attempt to parse json string if wrapped in markdown
                clean_json = content.strip()
                if clean_json.startswith("```"):
                    clean_json = clean_json.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(clean_json)
                info = ProductPriceInfo(**data)
            else:
                logger.warning(f"Unexpected response type from CommercePriceAgent: {type(content)}")
                return None

            if info:
                self._cache[cache_key] = info
            return info

        except Exception as e:
            logger.error(f"Failed to lookup product pricing for '{vision_result.object_name}': {e}")
            return None

# Singleton agent instance
commerce_agent = CommercePriceAgent()
