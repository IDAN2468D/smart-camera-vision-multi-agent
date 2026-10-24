import logging
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.models.google import Gemini
from agno.media import Image

from config.settings import settings
from models.detection_schema import VisionAnalysisResult, SpatialBoundingBox

logger = logging.getLogger(__name__)

class VisionPerceptionAgent:
    """Agent 1: Expert Computer Vision and OCR Perception Agent.
    
    Processes captured camera frames and outputs structured visual analysis
    using Google Gemini Vision.
    """

    def __init__(self, model_id: Optional[str] = None, api_key: Optional[str] = None):
        self.model_id = model_id or settings.MODEL_ID
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._agent = None

    def _get_agent(self) -> Agent:
        """Lazily initialize the Agno Agent with Gemini model and structured output schema."""
        if self._agent is None:
            model = Gemini(
                id=self.model_id,
                api_key=self.api_key if self.api_key else None
            )

            instructions = [
                "You are an expert AI Computer Vision & Human Perception Specialist.",
                "Your job is to thoroughly analyze the provided live camera frame and detect human faces, hands, gestures, held objects, and physical items.",
                "1. HUMAN FACES: Check if a person's face is visible. Set face_detected=True, note facial expression, gaze, and features (e.g. eyeglasses, beard).",
                "2. HANDS & GESTURES: Check if human hands, palms, fingers, or gestures are visible (e.g., open palm, waving, thumbs up, pointing, holding an object). Set hands_detected=True.",
                "3. OBJECTS & ITEMS: Detect any physical objects held by hand or in the scene (e.g. Smartwatch, Smartphone, Pen, Coffee Mug, Bottle, Headphones, Keys, Mouse). If the product has recognizable brand cues, specify the exact brand & model (e.g. Apple Watch Ultra, Logitech MX Master, iPhone 15, Sony WH-1000XM5).",
                "4. PRIMARY FOCUS (object_name): Identify the main subject/focus. If the user is holding or presenting an item, PRIORITIZE naming that specific item/product. If displaying a hand or gesture, name the hand/gesture. If looking at the camera without held objects, name the person/face.",
                "5. ALL DETECTED ENTITIES: Enumerate all recognized elements in detected_entities (e.g. ['Human Face', 'Right Hand', 'Apple Watch Ultra']). Always include any held or visible product here.",
                "6. OCR TEXT & BRANDS: Read and extract any visible text, brand logos, model numbers, or writing on screens, clothing, dials, or objects into detected_text.",
                "7. Provide an objective visual_description and a high-accuracy confidence score.",
                "8. SPATIAL BOUNDING BOXES: For primary detected items or faces, produce spatial_bboxes containing label, confidence (0.0-1.0), normalized coordinates x_min, y_min, x_max, y_max (between 0.0 and 1.0), and horizontal pan_x from -1.0 (left) to 1.0 (right)."
            ]

            # Support both output_schema (Agno 3.x) and response_model (Agno 2.x)
            kwargs = {
                "name": "VisionPerceptionAgent",
                "model": model,
                "fallback_models": [
                    Gemini(id="gemini-3.5-flash", api_key=self.api_key if self.api_key else None),
                    Gemini(id="gemini-3.8-flash", api_key=self.api_key if self.api_key else None)
                ],
                "instructions": instructions,
                "markdown": False
            }
            if "output_schema" in Agent.__init__.__code__.co_varnames:
                kwargs["output_schema"] = VisionAnalysisResult
            elif "response_model" in Agent.__init__.__code__.co_varnames:
                kwargs["response_model"] = VisionAnalysisResult

            self._agent = Agent(**kwargs)
        return self._agent

    def analyze_frame(self, image_path: str) -> VisionAnalysisResult:
        """Analyze an image frame from disk and return structured VisionAnalysisResult.
        
        Args:
            image_path: Absolute or relative file path to the JPEG/PNG image.
            
        Returns:
            VisionAnalysisResult instance with object name, category, OCR text, confidence, description.
        """
        img_file = Path(image_path)
        if not img_file.exists():
            raise FileNotFoundError(f"Image frame not found at: {image_path}")

        logger.info(f"VisionPerceptionAgent processing frame: {image_path}")
        
        # Guard against placeholder API key
        if not self.api_key or "YOUR_GEMINI_API_KEY" in self.api_key:
            logger.warning("No valid GEMINI_API_KEY provided in .env. Returning simulated perception result for verification.")
            return VisionAnalysisResult(
                object_name="Coffee Mug",
                category="Drinkware",
                detected_text="Ceramic Coffee Co.",
                confidence=0.96,
                visual_description="A white ceramic coffee mug with black lettering, placed on an office desk.",
                spatial_bboxes=[
                    SpatialBoundingBox(
                        label="Coffee Mug",
                        confidence=0.96,
                        x_min=0.35,
                        y_min=0.3,
                        x_max=0.65,
                        y_max=0.75,
                        pan_x=0.0
                    )
                ]
            )

        # Optimize image size (max 800px) for ultra-fast TLS transfer and reduced token latency
        target_img_path = img_file
        try:
            from PIL import Image as PILImage
            if img_file.stat().st_size > 150_000:
                with PILImage.open(img_file) as im:
                    if max(im.size) > 800:
                        im.thumbnail((800, 800))
                        opt_path = img_file.with_name(f"opt_{img_file.name}")
                        im.convert("RGB").save(opt_path, "JPEG", quality=85)
                        target_img_path = opt_path
        except Exception as opt_err:
            logger.debug(f"Image preprocessing skipped: {opt_err}")

        agent = self._get_agent()
        image_input = Image(filepath=target_img_path)
        
        prompt = (
            "Analyze everything visible in this camera frame: detect human faces, hands, gestures, and any physical objects. "
            "Set face_detected and hands_detected booleans, list all detected entities in detected_entities, "
            "identify the primary focus in object_name and its category, extract any detected_text via OCR, "
            "and provide a detailed visual_description."
        )

        response = agent.run(
            input=prompt,
            images=[image_input]
        )

        content = response.content
        if isinstance(content, VisionAnalysisResult):
            return content
        elif isinstance(content, dict):
            return VisionAnalysisResult(**content)
        elif isinstance(content, str):
            try:
                return VisionAnalysisResult.model_validate_json(content)
            except Exception:
                # In case model returned raw text, create fallback instance
                return VisionAnalysisResult(
                    object_name="Detected Object",
                    category="General",
                    detected_text=None,
                    confidence=0.85,
                    visual_description=content
                )
        else:
            raise TypeError(f"Unexpected response content type: {type(content)}")

# Singleton agent instance
vision_agent = VisionPerceptionAgent()
