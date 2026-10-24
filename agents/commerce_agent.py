import json
import logging
from typing import Optional
from urllib.parse import quote_plus
from agno.agent import Agent
from agno.models.google import Gemini
from config.settings import settings
from models.detection_schema import VisionAnalysisResult, ProductPriceInfo

logger = logging.getLogger(__name__)

NON_COMMERCIAL_EXACT = {
    "human", "person", "human face", "face", "man", "woman", "hand", "hands",
    "right hand", "left hand", "palm", "open palm", "thumbs up", "thumbs down",
    "finger", "gesture", "anatomy", "wall", "ceiling", "background", "empty room",
    "anatomy/hands", "nature", "animal", "body"
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
                "1. If OCR text or brand names or physical details are visible, identify the exact real model and brand (e.g. Apple Watch Ultra 2 GPS + Cellular 49mm, Logitech MX Master 3S, Sony WH-1000XM5, Stanley Quencher Cup 40oz).",
                "2. Provide a realistic estimated price range in Israel in ILS (₪) formatted like '₪3,150 - ₪3,690' or '₪380 - ₪450'.",
                "3. In specs_summary, provide 2-3 key technical highlights in clean, professional Hebrew.",
                "4. In store_name, specify 'Zap השוואת מחירים (zap.co.il)'.",
                "5. In source_url, provide an authentic Zap search link formatted as: https://www.zap.co.il/search.aspx?keyword={encoded_model}",
                "6. Output strictly according to the ProductPriceInfo schema."
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

    def get_commercial_candidate(self, vision_result: VisionAnalysisResult) -> Optional[str]:
        """Extract the best commercial product candidate name from the vision result."""
        obj = (vision_result.object_name or "").strip()
        obj_lower = obj.lower()

        # If object_name is already a specific physical product
        if obj_lower not in NON_COMMERCIAL_EXACT and not any(nc in obj_lower for nc in ["human", "anatomy", "gesture", "palm", "thumbs", "face", "hand"]):
            return obj

        # Otherwise look into detected_entities for a visible or held product
        for entity in vision_result.detected_entities:
            e_clean = entity.strip()
            e_lower = e_clean.lower()
            if e_lower not in NON_COMMERCIAL_EXACT and not any(nc in e_lower for nc in ["human", "anatomy", "gesture", "palm", "thumbs", "face", "hand"]):
                return e_clean

        # If detected_text has brand name or text, use that as candidate
        if vision_result.detected_text and len(vision_result.detected_text.strip()) > 2:
            return vision_result.detected_text.strip()

        return None

    def is_commercial_item(self, vision_result: VisionAnalysisResult) -> bool:
        """Determine if a vision result represents or contains an object/product worth evaluating."""
        candidate = self.get_commercial_candidate(vision_result)
        return candidate is not None

    def lookup_product(self, vision_result: VisionAnalysisResult) -> Optional[ProductPriceInfo]:
        """Perform pricing and technical lookup for a detected commercial item.
        
        Args:
            vision_result: Visual analysis details of the detected item.
            
        Returns:
            ProductPriceInfo instance or None if not applicable / failed.
        """
        candidate_item = self.get_commercial_candidate(vision_result)
        if not candidate_item:
            logger.debug(f"Item '{vision_result.object_name}' has no commercial product candidate. Skipping price lookup.")
            return None

        cache_key = f"{candidate_item.lower().strip()}_{str(vision_result.detected_text).lower().strip()}"
        if cache_key in self._cache:
            logger.info(f"[CommerceAgent] Returning cached pricing for: '{candidate_item}' (0ms)")
            return self._cache[cache_key]

        prompt = (
            f"You are an expert Israeli E-Commerce, Consumer Electronics & Gadget Valuation Specialist.\n"
            f"Identify the real, specific product model shown in this camera frame and provide accurate market pricing in Israel (ILS / ₪) and specs in Hebrew.\n\n"
            f"- Identified Product / Item: {candidate_item}\n"
            f"- Main Object: {vision_result.object_name}\n"
            f"- Category: {vision_result.category}\n"
            f"- Detected Entities: {', '.join(vision_result.detected_entities)}\n"
            f"- Visible Brand / OCR Text: {vision_result.detected_text or 'None'}\n"
            f"- Visual Description: {vision_result.visual_description}\n\n"
            f"Requirements:\n"
            f"1. model_name: Specify the EXACT real commercial product brand & model name (e.g. 'Apple Watch Ultra 2 GPS + Cellular 49mm', 'Logitech MX Master 3S', 'Sony WH-1000XM5', 'Samsung Galaxy S24 Ultra'). Do not use generic words.\n"
            f"2. estimated_price_ils: Realistic current Israeli retail price range formatted in ILS (₪), e.g. '₪3,150 - ₪3,690' or '₪380 - ₪450'.\n"
            f"3. specs_summary: 2-3 key technical highlights in clear, concise Hebrew.\n"
            f"4. store_name: 'Zap השוואת מחירים (zap.co.il)'\n"
            f"5. source_url: Authentic Zap search URL formatted like 'https://www.zap.co.il/search.aspx?keyword={candidate_item}'\n"
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
                # Capture live Playwright screenshot of the actual retail comparison page
                search_term = info.model_name or candidate_item
                try:
                    from services.browser_agent_service import browser_agent_service
                    capture_res = browser_agent_service.capture_retail_price(search_term)
                    if capture_res:
                        info.price_screenshot_base64 = capture_res.get("screenshot_base64")
                        info.store_name = capture_res.get("store_name", "Zap השוואת מחירים (zap.co.il)")
                        if not info.source_url or "http" not in info.source_url:
                            info.source_url = capture_res.get("url")
                except Exception as b_err:
                    logger.debug(f"[CommerceAgent] Browser screenshot skipped: {b_err}")

                # Ensure source_url is always a verified Zap comparison URL
                if not info.source_url or "http" not in info.source_url:
                    info.source_url = f"https://www.zap.co.il/search.aspx?keyword={quote_plus(search_term)}"

                if not info.store_name:
                    info.store_name = "Zap השוואת מחירים (zap.co.il)"

                self._cache[cache_key] = info
            return info

        except Exception as e:
            logger.error(f"Failed to lookup product pricing for '{candidate_item}': {e}")
            return None

# Singleton agent instance
commerce_agent = CommercePriceAgent()
