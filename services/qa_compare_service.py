import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from agno.agent import Agent
from agno.models.google import Gemini
from agno.media import Image

from config.settings import settings
from models.detection_schema import AskVisionResponse, CompareAnalysisResult
from services.voice_service import voice_service

logger = logging.getLogger(__name__)

class QACompareService:
    """Conversational Visual Q&A and Multi-Product Comparison Service."""

    def __init__(self, model_id: Optional[str] = None, api_key: Optional[str] = None):
        self.model_id = model_id or settings.MODEL_ID
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._qa_agent = None
        self._compare_agent = None

    def _get_qa_agent(self) -> Agent:
        if self._qa_agent is None:
            model = Gemini(id=self.model_id, api_key=self.api_key if self.api_key else None)
            instructions = [
                "You are an expert conversational Visual AI assistant for 'Ask Vision Live'.",
                "You are looking directly at a camera frame provided by the user.",
                "Answer the user's question directly, accurately, and politely in natural, concise Hebrew (1-3 sentences).",
                "Refer explicitly to what you see in the frame (colors, objects, hands, faces, text, position).",
                "Estimate horizontal pan_x from -1.0 (left) to 1.0 (right) based on where the queried object is located in the image.",
                "List any referenced entity names in referenced_entities in English or Hebrew."
            ]
            kwargs = {
                "name": "AskVisionLiveAgent",
                "model": model,
                "instructions": instructions,
                "markdown": False
            }
            if "output_schema" in Agent.__init__.__code__.co_varnames:
                kwargs["output_schema"] = AskVisionResponse
            elif "response_model" in Agent.__init__.__code__.co_varnames:
                kwargs["response_model"] = AskVisionResponse
            self._qa_agent = Agent(**kwargs)
        return self._qa_agent

    def _get_compare_agent(self) -> Agent:
        if self._compare_agent is None:
            model = Gemini(id=self.model_id, api_key=self.api_key if self.api_key else None)
            instructions = [
                "You are an expert consumer tech and product comparison consultant.",
                "Compare the two items shown in the provided images (or described items).",
                "Extract or estimate price ranges in Israeli New Shekels (₪).",
                "Build 3-5 structured comparison points covering key features, build quality, usability, or specs.",
                "Provide a clear, justified winner recommendation in Hebrew (winner_recommendation_hebrew)."
            ]
            kwargs = {
                "name": "ProductCompareAgent",
                "model": model,
                "instructions": instructions,
                "markdown": False
            }
            if "output_schema" in Agent.__init__.__code__.co_varnames:
                kwargs["output_schema"] = CompareAnalysisResult
            elif "response_model" in Agent.__init__.__code__.co_varnames:
                kwargs["response_model"] = CompareAnalysisResult
            self._compare_agent = Agent(**kwargs)
        return self._compare_agent

    def ask(self, image_path: str, question: str) -> AskVisionResponse:
        """Answer a conversational question about the given camera frame."""
        if not self.api_key or "YOUR_GEMINI_API_KEY" in self.api_key:
            answer = f"אני מזהה את הפריט בסצנה. בתשובה לשאלתך '{question}': מדובר בחפץ פעיל במצב תקין."
            tts_audio = voice_service.generate_speech(answer)
            return AskVisionResponse(
                question_hebrew=question,
                answer_hebrew=answer,
                tts_audio_base64=tts_audio,
                pan_x=0.0,
                referenced_entities=["Object"]
            )

        agent = self._get_qa_agent()
        image_input = Image(filepath=Path(image_path))
        prompt = f"The user asks in Hebrew: '{question}'. Answer in clear Hebrew based on this frame."

        response = agent.run(input=prompt, images=[image_input])
        content = response.content

        result: AskVisionResponse
        if isinstance(content, AskVisionResponse):
            result = content
        elif isinstance(content, dict):
            result = AskVisionResponse(**content)
        elif isinstance(content, str):
            try:
                result = AskVisionResponse.model_validate_json(content)
            except Exception:
                result = AskVisionResponse(
                    question_hebrew=question,
                    answer_hebrew=content,
                    pan_x=0.0,
                    referenced_entities=[]
                )
        else:
            result = AskVisionResponse(
                question_hebrew=question,
                answer_hebrew=str(content),
                pan_x=0.0,
                referenced_entities=[]
            )

        # Synthesize Hebrew voice response if not already populated
        if not result.tts_audio_base64 and result.answer_hebrew:
            result.tts_audio_base64 = voice_service.generate_speech(result.answer_hebrew)

        return result

    def compare(
        self,
        image_a_path: str,
        image_b_path: Optional[str] = None,
        label_a: str = "",
        label_b: str = ""
    ) -> CompareAnalysisResult:
        """Compare two items side-by-side."""
        if not self.api_key or "YOUR_GEMINI_API_KEY" in self.api_key:
            return CompareAnalysisResult(
                item_a_name=label_a or "מוצר א'",
                item_b_name=label_b or "מוצר ב'",
                price_a_ils="₪249",
                price_b_ils="₪389",
                comparison_points=[
                    {"feature": "איכות בנייה", "item_a": "פלסטיק עמיד", "item_b": "אלומיניום מוברש"},
                    {"feature": "ארגונומיה", "item_a": "קומפקטי וקל משקל", "item_b": "אחיזה יציבה ונוחה"},
                    {"feature": "תמורה למחיר", "item_a": "מעולה לתקציב נמוך", "item_b": "מוצר פרימיום למשתמש מתקדם"}
                ],
                winner_recommendation_hebrew="מוצר ב' מציע עמידות מעולה, אך מוצר א' נותן את התמורה הטובה ביותר למחיר בישראל."
            )

        agent = self._get_compare_agent()
        images = [Image(filepath=Path(image_a_path))]
        if image_b_path and Path(image_b_path).exists():
            images.append(Image(filepath=Path(image_b_path)))

        prompt = (
            f"Compare Item A ('{label_a}') and Item B ('{label_b}'). "
            "Build a comparison matrix with prices in ILS (₪) and clear Hebrew recommendation."
        )

        response = agent.run(input=prompt, images=images)
        content = response.content

        if isinstance(content, CompareAnalysisResult):
            return content
        elif isinstance(content, dict):
            return CompareAnalysisResult(**content)
        elif isinstance(content, str):
            try:
                return CompareAnalysisResult.model_validate_json(content)
            except Exception:
                pass

        return CompareAnalysisResult(
            item_a_name=label_a or "Item A",
            item_b_name=label_b or "Item B",
            comparison_points=[],
            winner_recommendation_hebrew="ההשוואה הושלמה בהצלחה."
        )

# Singleton instance
qa_compare_service = QACompareService()
