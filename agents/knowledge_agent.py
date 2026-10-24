import json
import logging
from typing import Optional, List, Dict, Any
from agno.agent import Agent
from agno.models.google import Gemini

from config.settings import settings
from dal.detection_repo import detection_repo
from models.detection_schema import VisionAnalysisResult

logger = logging.getLogger(__name__)

def check_detection_history(object_name: str) -> str:
    """Tool function: Query MongoDB Atlas to retrieve past detections for an object.
    
    Args:
        object_name: The name of the object to search for in historical records.
        
    Returns:
        JSON string containing the list of previous detection records (up to 3).
    """
    try:
        records = detection_repo.find_by_object_name(object_name=object_name, limit=3)
        return json.dumps(records, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error querying history tool for '{object_name}': {e}")
        return json.dumps({"error": str(e)})

class KnowledgeEnrichmentAgent:
    """Agent 2: Memory & Knowledge Enrichment Agent.
    
    Uses function calling / tools to cross-reference MongoDB Atlas detection history
    and synthesizes actionable contextual insights in Hebrew.
    """

    def __init__(self, model_id: Optional[str] = None, api_key: Optional[str] = None):
        self.model_id = model_id or settings.MODEL_ID
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._agent = None

    def _get_agent(self) -> Agent:
        """Lazily initialize the Agno Agent with Gemini model and the history tool."""
        if self._agent is None:
            model = Gemini(
                id=self.model_id,
                api_key=self.api_key if self.api_key else None
            )

            instructions = [
                "אתה סוכן זיכרון וידע מומחה (Knowledge & Memory Agent) עבור מערכת ראייה ממוחשבת.",
                "תפקידך לקבל תוצאות זיהוי של אובייקט, לבדוק בעזרת הכלי 'check_detection_history' האם הוא נסרק בעבר במסד הנתונים MongoDB Atlas,",
                "ולייצר סיכום תובנות הקשרי ומדויק בעברית בת 2 עד 3 משפטים בלבד.",
                "כללים להפקת התובנה בעברית:",
                "1. אם הפריט נסרק בעבר: ציין שהוא זוהה במערכת בעבר, פרט מתי נסרק לאחרונה ואילו מאפיינים/טקסט הופיעו.",
                "2. אם הפריט לא נסרק מעולם: ציין שזהו זיהוי ראשון של הפריט במאגר המערכת, והוסף משפט קצר על שימושו הנפוץ או מאפייניו.",
                "3. שמור על סגנון מקצועי, תמציתי וברור בעברית רהוטה ללא מריחת מילים מיותרות."
            ]

            self._agent = Agent(
                name="KnowledgeEnrichmentAgent",
                model=model,
                fallback_models=[
                    Gemini(id="gemini-3.5-flash", api_key=self.api_key if self.api_key else None),
                    Gemini(id="gemini-3.8-flash", api_key=self.api_key if self.api_key else None)
                ],
                tools=[check_detection_history],
                instructions=instructions,
                markdown=False
            )
        return self._agent

    def enrich(
        self,
        vision_result: VisionAnalysisResult,
        similar_items: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Enrich a vision analysis result by correlating with MongoDB history.
        
        Args:
            vision_result: The VisionAnalysisResult output from VisionPerceptionAgent.
            similar_items: Semantically similar past detections retrieved via Atlas Vector Search (Visual RAG).
            history: Optional pre-fetched detection records for the object (eliminates tool round-trip).
            
        Returns:
            Concise 2-3 sentence enrichment summary in Hebrew.
        """
        logger.info(f"KnowledgeEnrichmentAgent enriching: '{vision_result.object_name}'")
        similar_items = similar_items or []
        similar_names = [s.get("object_name") for s in similar_items if s.get("object_name")]

        # Pre-fetch history if not passed from orchestrator
        if history is None:
            history = detection_repo.find_by_object_name(vision_result.object_name, limit=3)

        # Guard against placeholder API key
        if not self.api_key or "YOUR_GEMINI_API_KEY" in self.api_key:
            if history:
                last_time = history[0].get("timestamp", "לאחרונה")
                return f"הפריט '{vision_result.object_name}' זוהה בעבר במערכת (סריקה קודמת: {last_time}). מדובר בפריט מוכר מקטגוריית {vision_result.category}."
            elif similar_names:
                return (
                    f"זהו זיהוי ראשון של '{vision_result.object_name}' במערכת, אך החיפוש הוויזואלי-סמנטי מצא פריטים דומים שנסרקו בעבר: "
                    f"{', '.join(dict.fromkeys(similar_names))}. הפריט שייך לקטגוריית {vision_result.category}."
                )
            else:
                return f"זהו זיהוי ראשון של '{vision_result.object_name}' במערכת. הפריט שייך לקטגוריית {vision_result.category} ונוסף כעת בהצלחה למאגר הנתונים."

        agent = self._get_agent()
        entities_str = ", ".join(vision_result.detected_entities) if vision_result.detected_entities else vision_result.object_name
        similar_str = "\n".join(
            f"  * {s.get('object_name')} (קטגוריה: {s.get('category')}, נסרק: {s.get('timestamp')}, דמיון: {s.get('similarity_score', 0.0) * 100:.0f}%)"
            for s in similar_items[:3]
        ) or "  * לא נמצאו פריטים דומים"

        history_str = "\n".join(
            f"  * נסרק בעבר בתאריך {h.get('timestamp')}: {h.get('visual_description', '')}"
            for h in history
        ) if history else "  * פריט זה לא נסרק מעולם בעבר (זיהוי ראשון במערכת)"

        query = (
            f"התקבל זיהוי חדש מהמצלמה:\n"
            f"- פוקוס מרכזי: {vision_result.object_name} (קטגוריה: {vision_result.category})\n"
            f"- אלמנטים שזוהו בפריים: {entities_str}\n"
            f"- זיהוי פנים: {'כן' if vision_result.face_detected else 'לא'} | זיהוי ידיים/מחוות: {'כן' if vision_result.hands_detected else 'לא'}\n"
            f"- טקסט OCR: {vision_result.detected_text or 'לא זוהה טקסט'}\n"
            f"- ודאות: {vision_result.confidence * 100:.1f}%\n"
            f"- תיאור ויזואלי: {vision_result.visual_description}\n"
            f"- היסטוריית סריקות קודמות במסד הנתונים:\n{history_str}\n"
            f"- פריטים דומים ויזואלית/סמנטית (Atlas Vector Search):\n{similar_str}\n\n"
            f"בהתבסס על ההיסטוריה והפריטים הדומים שסופקו לעיל, ספק סיכום העשרה מקצועי בעברית (2-3 משפטים בלבד) "
            f"המתייחס לאובייקטים, לפנים או למחוות שזוהו. אם יש היסטוריה ציין זאת, ואם זהו זיהוי ראשון ציין זאת במפורש."
        )

        response = agent.run(input=query)
        summary = str(response.content).strip() if response and response.content else ""
        if not summary:
            summary = f"פריט מסוג {vision_result.object_name} נרשם במערכת."
        return summary

# Singleton agent instance
knowledge_agent = KnowledgeEnrichmentAgent()
