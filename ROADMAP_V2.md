# 🚀 Master Prompt, PRD, SPEC & PLAN: שדרוגי דור הבא למערכת Vision AI Multi-Agent (v2.0)

מסמך זה מרכז את אפיון המוצר (**PRD**), המפרט הטכני (**SPEC**), תכנית העבודה (**PLAN**) ו-**Master Prompt** מוכן להרצה עבור שדרוג מערכת ה-**AI-First Multi-Agent** הקיימת (Next.js 14 Port 3002 + Flask API Port 5005 + Agno + Gemini 3.5 Flash Lite + MongoDB Atlas + OpenCV Desktop Feed + Docker Compose).

---

## 📋 חלק 1: אפיון מוצר — PRD (Product Requirements Document)

### 1.1 תקציר מנהלים וחזון מוצרי (Executive Summary & Vision)
מערכת ה-Vision AI הקיימת מספקת תשתית Production מקצה לקצה לזיהוי חזותי, חילוץ טקסט (OCR), זיהוי פנים וידיים, והעשרת ידע מבוססת היסטוריה (RAG) בעברית מול MongoDB Atlas. מטרת גרסה **v2.0** היא להפוך את המערכת מפלטפורמת סריקה מבוססת-לחיצה לחוויית **Zero-Touch Multimodal AI** בזמן אמת — הכוללת מעקב שלד ו-Bounding Boxes ב-60FPS, הפעלה ללא מגע באמצעות מחוות יד, סוכן קולי בעברית, חיפוש וקטורי חזותי, זיהוי ביומטרי אישי, סוכן מסחר וחיפוש רשת, תקשורת Push חיה (SSE), וגלריית צילומים עם ייצוא דוחות.

### 1.2 יעדי המוצר ומדדי הצלחה (Product Goals & KPIs)
* **חוויית Zero-Touch מלאה**: יכולת להפעיל ולעצור סריקות באמצעות מחוות יד (👍 / ✋) עם השהיית זיהוי מקומית של פחות מ-`50ms` וללא מגע במקלדת.
* **משוב רב-חושי בזמן אמת (Visual + Audio)**: רינדור שכבת HUD חיה (Bounding Boxes + 21 נקודות מפרקי יד) ב-`30-60 FPS` על גבי ה-Canvas בדפדפן וב-OpenCV, לצד הקראה קולית אוטומטית בעברית של תובנות ה-AI תוך פחות מ-`1.5 שניות` מסיום הסריקה.
* **זיכרון חזותי סמנטי (Visual RAG)**: איתור פריטים דומים ויזואלית מתוך MongoDB Atlas באמצעות Vector Search ברמת דיוק (Recall@5) של מעל `85%`, גם כאשר תיאור הטקסט שונה.
* **עדכון חי ללא Polling**: מעבר לארכיטקטורת Server-Sent Events (SSE) שמעדכנת את לוח הבקרה ב-Next.js תוך פחות מ-`100ms` מרגע שמירת הרשומה ב-MongoDB, תוך חיסכון של 90% מבקשות ה-HTTP המיותרות.

### 1.3 דרישות פונקציונליות לפי פיצ'רים (Functional Requirements)

#### פיצ'ר 1: Real-Time Landmark Tracking (MediaPipe / YOLO HUD)
* **תיאור**: ציור Bounding Boxes ירוקים סביב פנים וחפצים וציור שלד היד (21 מפרקים וחיבורים) בזמן אמת על גבי ה-HTML5 Canvas ב-Next.js ועל הפיד ב-OpenCV עוד לפני שליחת הפריים ל-Gemini.
* **דרישות**:
  * הרצת מודל קל-משקל בצד הלקוח (`@mediapipe/tasks-vision`) ובצד שולחן העבודה (`mediapipe` / `ultralytics YOLOv8n`).
  * שכבת Overlay שקופה בסגנון Cyberpunk עם קואורדינטות מנורמלות ומד FPS חי.

#### פיצ'ר 2: Gesture Control (שליטה במחוות יד ללא מגע)
* **תיאור**: הפעלת סריקה או עצירת מצב אוטומטי באמצעות מחוות יד מול המצלמה.
* **דרישות**:
  * מחוות **👍 (Thumbs Up)** המוחזקת למשך `800ms` (Debounce למניעת לחיצות שווא) מפעילה סריקת AI מיידית (שווה ערך למקש `SPACE`).
  * מחוות **✋ (Open Palm)** המוחזקת למשך `800ms` עוצרת/משהה את הסריקה האוטומטית.
  * חיווי ויזואלי של מד טעינה עגול (Progress Ring) סביב היד בעת החזקת המחווה.

#### פיצ'ר 3: Voice Agent (סוכן קולי בעברית - TTS)
* **תיאור**: הקראה קולית רהוטה בעברית של התובנות שהופקו על ידי ה-`KnowledgeEnrichmentAgent` מיד עם סיום הסריקה.
* **דרישות**:
  * תמיכה במנוע TTS היברידי: קצה שרת (`edge-tts` בקול עברי טבעי `he-IL-AvriNeural` / `he-IL-HilaNeural` או Google Cloud TTS) עם Fallback מובנה ל-Web Speech API (`window.speechSynthesis` מוגדר ל-`he-IL`) בדפדפן.
  * כפתור Mute/Unmute בלוח הבקרה של Next.js ואנימציית גלי קול (Audio Waveform) בזמן הדיבור.

#### פיצ'ר 4: MongoDB Vector Search (RAG חזותי)
* **תיאור**: הפיכת התמונות הנסרקות ל-Vector Embeddings ושמירתן ב-MongoDB Atlas לצורך חיפוש פריטים "דומים ויזואלית".
* **דרישות**:
  * חילוץ וקטור אמבדינג (`768` או `1408` ממדים) לכל פריים/אובייקט שנסרק ושמירתו בשדה `image_embedding` באוסף `detections`.
  * הגדרת Atlas Vector Search Index (`vector_index`) וביצוע שאילתת `$vectorSearch` בתוך ה-`KnowledgeEnrichmentAgent` כדי לזהות אם אותו חפץ או חפץ דומה נסרק בעבר.

#### פיצ'ר 5: Face Recognition & Personalization (זיהוי פנים ופרסונליזציה)
* **תיאור**: זיהוי פנים ספציפיות של משתמשים רשומים (כגון "עידן") והתאמת התובנות וההיסטוריה באופן אישי.
* **דרישות**:
  * אוסף ייעודי `known_faces` ב-MongoDB השומר חתימות פנים וקטוריות (128D/512D Face Embeddings) ושם המשתמש.
  * פנייה אישית בשם המשתמש בתובנות ה-AI ובפלט הקולי ("שלום עידן, זיהיתי שאתה מחזיק שוב את...").

#### פיצ'ר 6: Price & Web Search Agent (סוכן מחירים וחיפוש רשת)
* **תיאור**: סוכן Agno חדש המצויד בכלי חיפוש אינטרנטי לאיתור דגם מדויק של מוצר, מפרט טכני וטווח מחירים עדכני בישראל (₪) ובעולם ($).
* **דרישות**:
  * מופעל אוטומטית כאשר `VisionPerceptionAgent` מזהה מוצר מסחרי/אלקטרוניקה/גאדג'ט.
  * מחזיר אובייקט מובנה עם שם דגם, מחיר מוערך, מפרט תמציתי וקישור למקור.

#### פיצ'ר 7: WebSockets / Server-Sent Events (SSE Realtime Push)
* **תיאור**: עדכון מיידי בדחיפה (Push) של ממשק ה-Next.js ברגע שמתבצעת סריקה (בין אם מהדפדפן ובין אם מ-OpenCV Desktop Feed), ללא צורך ב-Polling.
* **דרישות**:
  * נקודת קצה `/api/stream` ב-Flask המשדרת אירועי `detection_created` ו-`agent_status` בפורמט SSE תקני.
  * חיבור `EventSource` ב-Next.js שמעדכן את הכרטיס החי ואת ציר ההיסטוריה בזמן אמת.

#### פיצ'ר 8: Snapshot Gallery & PDF/Excel Export (גלריית תמונות וייצוא דוחות)
* **תיאור**: שמירת תמונת ממוזערת (Thumbnail WebP Base64 דחוס) של הפריים שנסרק לצד כל רשומה ב-MongoDB, תצוגת גלריה ב-Next.js, וייצוא דוח סריקות מרוכז.
* **דרישות**:
  * דחיסת התמונה ל-WebP ברזולוציית `320x180` (עד `15KB` לרשומה) ושמירתה בשדה `thumbnail_base64`.
  * תצוגת Lightbox בגלריית ההיסטוריה ב-Next.js וכפתורי ייצוא ל-PDF (בעברית RTL) ו-Excel (`.xlsx` / `.csv`).

---

## 🛠️ חלק 2: מפרט ארכיטקטורה טכני — SPEC (Technical Specification)

### 2.1 ארכיטקטורת המערכת המשודרגת (System Architecture v2.0)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      Next.js 14 Web Frontend (Port 3002, RTL)                    │
│  • MediaPipe Hands/Face 60FPS HUD Canvas   • Gesture Trigger Ring (👍 / ✋)      │
│  • SSE Live Stream Client (EventSource)    • Voice TTS Player & Waveform         │
│  • Snapshot Gallery & Lightbox             • PDF / Excel Report Exporter         │
└───────────────────┬──────────────────────────────────────────▲───────────────────┘
                    │ HTTP POST /api/analyze (Reverse Proxy)   │ SSE Push (/api/stream)
┌───────────────────▼──────────────────────────────────────────┴───────────────────┐
│                         Flask REST & SSE API Controller (Port 5005)              │
│  • /api/health  • /api/detections  • /api/analyze  • /api/stream  • /api/export  │
└───────────────────────────────────────────┬──────────────────────────────────────┘
                                            │
                            ┌───────────────▼───────────────┐
                            │   MultiAgentOrchestrator      │
                            │  (Agno + Pydantic v2 + SSE)   │
                            └───────────────┬───────────────┘
        ┌───────────────────┬───────────────┼───────────────┬───────────────────┐
        ▼                   ▼               ▼               ▼                   ▼
┌───────────────┐  ┌─────────────────┐ ┌──────────┐ ┌───────────────┐  ┌─────────────────┐
│ Vision Agent  │  │ Biometric &     │ │ Commerce │ │ Knowledge RAG │  │ Voice TTS       │
│ Gemini 3.5    │  │ Embedding Svc   │ │ & Price  │ │ Agent (Hebrew)│  │ Synthesizer     │
│ Flash Lite    │  │ • Face Match    │ │ Agent    │ │ • Regex +     │  │ • Edge-TTS he-IL│
│ (Triple       │  │ • Vector Embed  │ │ • Web    │ │   Atlas Vector│  │ • Audio Stream  │
│  Fallback)    │  │ • WebP Thumb    │ │   Search │ │   Search      │  │                 │
└───────────────┘  └────────┬────────┘ └────┬─────┘ └───────┬───────┘  └─────────────────┘
                            │               │               │
                            └───────────────▼───────────────┘
                                    ┌───────────────┐
                                    │ MongoDB Atlas │
                                    │ • detections  │
                                    │ • known_faces │
                                    │ • vector_idx  │
                                    └───────────────┘
```

### 2.2 מודלי נתונים וסכמות (Data Models — Pydantic v2 & TypeScript/Zod)

#### Backend Schema (`models/detection.py` — Pydantic v2)
```python
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    label: str = Field(..., description="סוג האובייקט או הפנים שזוהו")
    confidence: float = Field(..., ge=0.0, le=1.0)
    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)

class ProductPriceInfo(BaseModel):
    model_name: str = Field(..., description="שם הדגם המדויק של המוצר")
    estimated_price_ils: Optional[str] = Field(None, description="טווח מחירים בשקלים (₪)")
    specs_summary: Optional[str] = Field(None, description="תקציר מפרט טכני בעברית")
    source_url: Optional[str] = Field(None, description="קישור למקור המידע")

class VisualSimilarMatch(BaseModel):
    detection_id: str
    timestamp: datetime
    similarity_score: float
    summary_hebrew: str
    thumbnail_base64: Optional[str] = None

class DetectionRecordV2(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_source: str = Field(default="manual_space", description="manual_space | auto_timer | gesture_thumbs_up | opencv_desktop")
    
    # Vision Perception
    detected_objects: List[str] = Field(default_factory=list)
    ocr_text: Optional[str] = Field(None)
    face_detected: bool = Field(default=False)
    recognized_person_name: Optional[str] = Field(None, description="שם האדם שזוהה ביומטרית, למשל 'עידן'")
    hands_detected: bool = Field(default=False)
    gesture_detected: Optional[str] = Field(None, description="thumbs_up | open_palm | pointing | none")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    
    # Enrichment & Multi-Agent Outputs
    hebrew_insight: str = Field(..., description="תובנה הקשרית בעברית רהוטה")
    product_info: Optional[ProductPriceInfo] = Field(None)
    similar_past_detections: List[VisualSimilarMatch] = Field(default_factory=list)
    
    # Media & Vector Storage
    thumbnail_base64: Optional[str] = Field(None, description="תמונת WebP ממוזערת בפורמט Base64")
    image_embedding: Optional[List[float]] = Field(None, exclude=True, description="וקטור אמבדינג לחיפוש ב-MongoDB Atlas")
    tts_audio_base64: Optional[str] = Field(None, description="קובץ שמע MP3 בפורמט Base64 להקראה מיידית")
    model_used: str = Field(default="gemini-3.5-flash-lite")
```

#### Frontend Schema (`src/lib/schemas/detection.ts` — Zod)
```typescript
import { z } from "zod";

export const ProductPriceInfoSchema = z.object({
  model_name: z.string(),
  estimated_price_ils: z.string().nullable().optional(),
  specs_summary: z.string().nullable().optional(),
  source_url: z.string().url().nullable().optional(),
});

export const DetectionRecordV2Schema = z.object({
  _id: z.string().optional(),
  timestamp: z.string(),
  trigger_source: z.enum(["manual_space", "auto_timer", "gesture_thumbs_up", "opencv_desktop"]),
  detected_objects: z.array(z.string()),
  ocr_text: z.string().nullable().optional(),
  face_detected: z.boolean(),
  recognized_person_name: z.string().nullable().optional(),
  hands_detected: z.boolean(),
  gesture_detected: z.string().nullable().optional(),
  confidence_score: z.number().min(0).max(1),
  hebrew_insight: z.string(),
  product_info: ProductPriceInfoSchema.nullable().optional(),
  thumbnail_base64: z.string().nullable().optional(),
  tts_audio_base64: z.string().nullable().optional(),
  model_used: z.string(),
});

export type DetectionRecordV2 = z.infer<typeof DetectionRecordV2Schema>;
```

### 2.3 הגדרת אינדקס חיפוש וקטורי ב-MongoDB Atlas (`vector_index`)
יש להגדיר ב-MongoDB Atlas (`cluster0.purdk.mongodb.net`) על האוסף `detections` את האינדקס הבא:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "image_embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "recognized_person_name"
    }
  ]
}
```

### 2.4 מפרט נקודות קצה חדשות ב-Flask API (Port 5005)
1. `POST /api/analyze`:
   * **קלט**: `{ "image_base64": "...", "trigger_source": "gesture_thumbs_up", "enable_tts": true, "enable_price_lookup": true }`
   * **תהליך**:
     1. יוצר `thumbnail_base64` (WebP 320x180) ומחלץ `image_embedding` וזיהוי פנים (`recognized_person_name`).
     2. מריץ את `VisionPerceptionAgent` (עם Triple Fallback: `gemini-3.5-flash-lite` -> `gemini-3.5-flash` -> `gemini-3.8-flash`).
     3. במידה וזוהה מוצר מסחרי, מפעיל במקביל את `PriceWebSearchAgent`.
     4. מפעיל את `KnowledgeEnrichmentAgent` המבצע גם חיפוש טקסטואלי וגם `$vectorSearch` ב-MongoDB Atlas, ומנסח תובנה אישית בעברית.
     5. מסנתז קול בעברית (`tts_audio_base64`) ושומר את הרשומה ב-MongoDB.
     6. משדר את הרשומה החדשה לכל הלקוחות המחוברים ל-SSE (`/api/stream`).
2. `GET /api/stream`:
   * **פלט**: זרם `text/event-stream` (SSE) עם אירועי `agent_step` (למשל: `"מנתח תמונה..."`, `"מחפש מחירים ברשת..."`, `"מפיק קול בעברית..."`) ואירוע סופי `detection_complete`.
3. `POST /api/faces/enroll`:
   * **קלט**: `{ "person_name": "עידן", "image_base64": "..." }` — רישום חתימת פנים ביומטרית לאוסף `known_faces`.
4. `GET /api/export?format=pdf|xlsx&limit=50`:
   * **פלט**: הורדת קובץ דוח מרוכז בעברית (RTL) הכולל תמונות Thumbnail, חותמות זמן, אובייקטים, מחירים ותובנות.

---

## 🗓️ חלק 3: תכנית עבודה ומימוש — PLAN (Implementation Roadmap)

תכנית העבודה מחולקת ל-**4 ספרינטים ממוקדים** הבנויים לפי סדר עדיפויות הנדסי (מתשתית ה-Core ו-3 הפיצ'רים המומלצים ביותר ועד לפיצ'רי ה-AI המתקדמים):

| שלב / ספרינט | פיצ'רים כלולים | רכיבי מערכת מושפעים | סטטוס ביצוע | קריטריון הצלחה (Definition of Done) |
| :--- | :--- | :--- | :--- | :--- |
| **Sprint 1: Core UX, Gestures & Snapshots** | • Gesture Control (👍 / ✋)<br>• Snapshot Gallery & Lightbox<br>• WebP Compression | `WebcamHUD.tsx`, `DetectionHistory.tsx`, `thumbnail_service.py` | ✅ **הושלם ונבדק** | סריקת מחווה 👍 מפעילה סריקת AI מיידית; WebP 320x180 נשמר ב-MongoDB ומוצג בגלריה עם Lightbox. |
| **Sprint 2: Voice AI & Realtime SSE Push** | • Voice Agent (TTS בעברית)<br>• Server-Sent Events (SSE) | `voice_service.py`, `sse_service.py`, `api_controller.py`, `page.tsx` | ✅ **הושלם ונבדק** | סיום סריקה משדר Push מיידי לדפדפן ב-SSE (`/api/stream`) ומקריא בקול עברי טבעי (`he-IL-AvriNeural`) עם נגן גלי קול. |
| **Sprint 3: Visual RAG & Biometrics** | • Biometrics & Person Schema<br>• Face Enrollment API | `detection_schema.py`, `api_controller.py` (`/api/faces/enroll`), `dal/` | ✅ **הושלם ונבדק** | סכמת נתונים מורחבת לשמירת וקטורים, שמות משתמשים ונקודת קצה לרישום פנים. |
| **Sprint 4: Commerce Agent & Reporting** | • Price & Commerce Agent<br>• PDF / Excel Report Export | `commerce_agent.py`, `export_service.py`, `api_controller.py`, Next.js UI | ✅ **הושלם ונבדק** | זיהוי מוצר מציג כרטיס מחיר ב-₪ ומפרט בעברית; כפתורי אקסל ו-PDF מפיקים דוחות מעוצבים ישירות מהדפדפן. |

### פירוט משימות טכניות לפי שלבים:

#### שלב 1: שכבת הראייה בזמן אמת, שליטה במחוות וגלריית צילומים (Sprint 1)
1. **דחיסת Snapshots ב-Backend**: הוספת פונקציית `generate_webp_thumbnail(image_bytes)` ב-Flask בעזרת `Pillow` / `cv2` שממירה כל פריים ל-WebP בגודל `320x180` ושומרת ב-`thumbnail_base64`.
2. **MediaPipe Hands & Face בדפדפן וב-OpenCV**:
   * ב-Next.js: שילוב `@mediapipe/tasks-vision` (`HandLandmarker` + `FaceDetector`) שרץ בתוך `requestAnimationFrame` על גבי `<canvas>` שקוף מעל ה-`<video>`.
   * בנית לוגיקת זיהוי מחוות (`detectGesture(landmarks)`):
     * **Thumbs Up (👍)**: קצה האגודל (Landmark 4) גבוה משמעותית ממפרק האגודל (Landmark 2) בעוד קצות האצבעות האחרות (8, 12, 16, 20) מקופלים מתחת למפרקים האמצעיים (6, 10, 14, 18).
     * **Open Palm (✋)**: כל 5 קצות האצבעות פתוחים וגבוהים מהמפרקים שלהם.
   * הוספת מנגנון Hold Timer של `800ms` + Cooldown של `5 שניות` בין סריקות מחווה.
3. **שדרוג רכיב ההיסטוריה ב-Next.js**: הצגת התמונה הממוזערת לצד כל כרטיס בהיסטוריה, עם מודאל הגדלה (Lightbox) בלחיצה.

#### שלב 2: סוכן קולי בעברית ודחיפת אירועים בזמן אמת SSE (Sprint 2)
1. **מודול `VoiceAgentService` ב-Backend**:
   * התקנת `edge-tts` והגדרת קול `he-IL-AvriNeural` (או `he-IL-HilaNeural`).
   * יצירת פונקציה אסינכרונית המקבלת את `hebrew_insight`, מפיקה זרם אודיו MP3 בזיכרון (`io.BytesIO`), ומקודדת ל-`tts_audio_base64`.
   * הוספת Fallback בצד הלקוח (`window.speechSynthesis`) למקרה שהשרת במצב Offline.
2. **תשתית SSE ב-Flask וב-Next.js**:
   * הוספת מחלקת `SSEBroadcaster` ב-Flask המנהלת תור `queue.Queue` לכל לקוח מחובר ב-`/api/stream`.
   * שידור שלבי הביניים של הסוכנים בזמן אמת (`vision_started`, `rag_querying`, `tts_generating`, `detection_saved`) כך שהמשתמש רואה ב-HUD בדיוק איזה סוכן עובד כרגע.

#### שלב 3: חיפוש וקטורי ב-MongoDB Atlas וזיהוי פנים ביומטרי (Sprint 3)
1. **חילוץ Embeddings וחיפוש `$vectorSearch`**:
   * יצירת שירות `EmbeddingService` המפיק וקטור אמבדינג לתמונה ושומר אותו ב-MongoDB.
   * הוספת כלי חדש ל-`KnowledgeEnrichmentAgent` בשם `find_visually_similar_detections(image_embedding)` שמבצע Aggregation Pipeline עם `$vectorSearch` ומחזיר את 3 הסריקות הדומות ביותר מהעבר.
2. **זיהוי פנים פרסונלי**:
   * השוואת וקטור הפנים שזוהה מול אוסף `known_faces` ב-MongoDB (Cosine Similarity > 0.75).
   * הזרקת שם המשתמש (`recognized_person_name`) לפרומפט המערכת של `KnowledgeEnrichmentAgent`.

#### שלב 4: סוכן מחירים וחיפוש רשת + ייצוא דוחות PDF/Excel (Sprint 4)
1. **הקמת `PriceWebSearchAgent`**:
   * סוכן Agno חדש המצויד ב-Search Tool, המופעל כאשר מזוהה מוצר מסחרי, ומחזיר `ProductPriceInfo` מאומת.
2. **ייצוא דוחות (PDF / Excel)**:
   * הוספת נקודת קצה `/api/export` ב-Flask וכפתור "ייצוא דוח סריקות" בלוח הבקרה של Next.js.

---

## 🤖 חלק 4: הפרומפט המלא להרצה — MASTER PROMPT (Copy & Paste)

העתק את הפרומפט הבא והדבק אותו ישירות לסוכן הפיתוח שלך (Cursor / Windsurf / Claude Code / Agno Coding Agent) כדי לממש את הפיצ'רים מקצה לקצה:

```markdown
# 🎯 ROLE & MISSION
אתה Senior Principal AI Systems Architect & Full-Stack Lead Engineer.
המשימה שלך היא לשדרג את מערכת ה-**AI-First Multi-Agent Vision Platform** הקיימת שלנו לגרסה **v2.0**, תוך שמירה קפדנית על יציבות ארכיטקטורת ה-Production הקיימת, תמיכה מלאה בעברית (RTL), ועמידות מלאה בקונטיינרים של Docker.

---

# 🏛️ CURRENT SYSTEM CONTEXT (DO NOT BREAK)
המערכת הקיימת בנויה מ:
1. **Backend (Flask REST API on Port 5005 + Agno Framework)**:
   - `VisionPerceptionAgent`: מנתח פריימים, מחלץ OCR, ומזהה פנים (`face_detected`), ידיים (`hands_detected`) וחפצים.
   - `KnowledgeEnrichmentAgent`: מצויד ב-Tool (`check_detection_history`) מול MongoDB ומפיק תובנה בעברית.
   - `MultiAgentOrchestrator`: מתזמר את הסוכנים ומחזיר `DetectionRecord` מאומת ב-Pydantic v2.
   - **Triple Fallback**: מעבר אוטומטי בין `gemini-3.5-flash-lite` -> `gemini-3.5-flash` -> `gemini-3.8-flash`.
2. **Database (DAL & MongoDB Atlas)**:
   - מחובר ל-`cluster0.purdk.mongodb.net` עם שמירת UTC Timestamps ואינדוקס Regex.
3. **Desktop Feed (OpenCV)**:
   - HUD חי במצלמת 2K עם מקשי שליטה `SPACE` (ידני), `A` (אוטומטי כל 8 שניות), ו-`Q` (יציאה).
4. **Frontend (Next.js 14 on Port 3002)**:
   - ממשק Cyberpunk/Glassmorphic בעברית RTL, מצלמת רשת בדפדפן, ו-Dynamic Reverse Proxy ל-Port 5005.
5. **Containers**:
   - `vision_ai_backend` ו-`vision_ai_frontend` ב-Docker Compose.

---

# 🚀 NEW FEATURES TO IMPLEMENT (STEP-BY-STEP)

ממש את השדרוגים הבאים בצורה מודולרית ונקייה לפי סדר השלבים הבא:

### Phase 1: Real-Time Landmark HUD, Gesture Triggering (👍 / ✋) & Snapshot Gallery
1. **Real-Time Landmark Tracking & Gesture Control**:
   - ב-Frontend (Next.js 14) וב-OpenCV Desktop Feed: שלב את MediaPipe Hands & Face Detection לציור שכבת HUD חיה (Bounding Boxes ירוקים סביב פנים + שלד יד עם 21 מפרקים) ב-60FPS על גבי ה-Canvas לפני שליחת התמונה ל-AI.
   - הוסף מנוע זיהוי מחוות יד ללא מגע (Zero-Touch Gesture Engine):
     - החזקת מחוות **👍 (Thumbs Up)** למשך `800ms` רצופים (עם טבעת טעינה ויזואלית על ה-HUD ו-Cooldown של 5 שניות) מפעילה אוטומטית סריקת AI (`trigger_source: "gesture_thumbs_up"`).
     - החזקת מחוות **✋ (Open Palm)** למשך `800ms` עוצרת/משהה את מצב הסריקה האוטומטי.
2. **Snapshot Compression & Gallery**:
   - ב-Flask Backend: בכל סריקה, דחוס את הפריים שצולם לתמונת Thumbnail בפורמט `WebP` (רזולוציה `320x180`, איכות 75) ושמור אותה כ-Base64 בשדה `thumbnail_base64` בתוך `DetectionRecord` ב-MongoDB Atlas.
   - ב-Next.js Frontend: שדרג את ציר ההיסטוריה לגלריית תמונות המציגה את ה-Snapshot המקורי לצד כל רשומה, כולל פתיחת התמונה במודאל (Lightbox) בלחיצה.

### Phase 2: Hebrew Voice Agent (TTS) & Realtime SSE Push
1. **Voice Agent (הקראת תובנות בעברית - TTS)**:
   - צור שירות `VoiceSynthesizerService` ב-Backend שמשתמש ב-`edge-tts` (קול `he-IL-AvriNeural` או `he-IL-HilaNeural`) להמרת `hebrew_insight` לאודיו MP3 מקודד ב-Base64 (`tts_audio_base64`).
   - ב-Next.js Frontend: נגן את קובץ השמע אוטומטית עם סיום הסריקה (עם Fallback ל-`window.speechSynthesis` ב-`he-IL`), הוסף אנימציית Audio Waveform חיה ב-HUD, וכפתור Mute/Unmute בלוח הבקרה.
2. **Server-Sent Events (SSE Realtime Push)**:
   - הוסף נקודת קצה `GET /api/stream` ב-Flask המשדרת אירועי זמן אמת (`agent_status` ו-`detection_created`).
   - חבר את ה-Next.js באמצעות `EventSource` כך שכל סריקה חדשה (גם אם הופעלה מ-OpenCV Desktop או ממחוות יד) תופיע מיידית בדפדפן ללא Polling, כולל הצגת סטטוס חי של הסוכן הפעיל כרגע בפייפליין.

### Phase 3: MongoDB Vector Search (Visual RAG) & Face Personalization
1. **Visual RAG (`$vectorSearch`)**:
   - הוסף הפקת וקטור אמבדינג (`image_embedding`) לכל סריקה ושמור אותו ב-MongoDB Atlas.
   - הוסף ל-`KnowledgeEnrichmentAgent` כלי חדש בשם `search_visually_similar_items` שמבצע שאילתת `$vectorSearch` ב-MongoDB Atlas ומצליב פריטים דומים ויזואלית מהעבר בתוך התובנה העברית.
2. **Face Recognition & Personalization**:
   - הוסף תמיכה בזיהוי פנים מוכרות מתוך אוסף `known_faces` ב-MongoDB (כולל Endpoint לרישום פנים `POST /api/faces/enroll`).
   - כאשר מזוהה משתמש מוכר (למשל "עידן"), שמור זאת ב-`recognized_person_name` והנחה את הסוכן לפנות אליו אישית בשמו בתובנה הכתובה והקולית.

### Phase 4: Price & Web Search Agent + PDF/Excel Export
1. **Price & Web Search Agent**:
   - הוסף סוכן Agno חדש (`CommercePriceAgent`) המצויד בכלי חיפוש אינטרנטי. כאשר `VisionPerceptionAgent` מזהה מוצר מסחרי/אלקטרוניקה, הסוכן ישלוף את שם הדגם המדויק, מפרט תמציתי וטווח מחירים בשקלים (₪), ויוסיף אותם לאובייקט `product_info`.
2. **Report Export (PDF / Excel)**:
   - הוסף נקודת קצה `GET /api/export?format=xlsx|pdf` ב-Flask וכפתורי הורדה ב-Next.js להפקת דוח סריקות מרוכז בעברית הכולל תמונות ממוזערות, חותמות זמן, אובייקטים ותובנות.

---

# 🛡️ STRICT ENGINEERING CONSTRAINTS
1. **Backward Compatibility**: אל תשבור אף Endpoint קיים (`/api/health`, `/api/detections`, `/api/analyze`) ואל תפגע במנגנון ה-Triple Fallback של מודלי Gemini.
2. **Strict Validation**: כל השדות החדשים חייבים להיות מוגדרים עם ערכי ברירת מחדל (`Optional` / `default`) ב-Pydantic v2 בשרת וב-Zod בלקוח כדי שרשומות היסטוריות ב-MongoDB ימשיכו להיטען ללא שגיאות.
3. **Performance & Non-Blocking**: ציור ה-Landmarks חייב לרוץ ב-60FPS מבלי לחסום את ה-Main Thread, ויצירת ה-TTS או חיפוש המחירים לא יפילו את הסריקה גם אם שירות חיצוני איטי (Graceful Degradation).
4. **Hebrew RTL & Cyberpunk UI**: שמור על עיצוב ה-Glassmorphic/Cyberpunk הקיים ב-Next.js 14 עם תמיכה מלאה ב-`dir="rtl"`.
5. **Docker Ready**: עדכן את `requirements.txt`, `package.json`, ו-`docker-compose.yml` עם כל הספריות החדשות הנדרשות.
```
