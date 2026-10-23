# 📐 SPEC: Technical Specification

## 2.1 Tech Stack
- **Language:** Python 3.11+
- **AI & Agents Framework:** `agno`, `google-genai` (Model: `gemini-2.5-flash`)
- **Computer Vision:** `opencv-python` (OpenCV), `pillow`
- **Backend API:** `flask`
- **Database:** MongoDB Atlas (`pymongo`, `dnspython`)
- **Validation & Env:** `pydantic`, `python-dotenv`

## 2.2 Modular Directory Structure
```text
camera-recognition-agents/
├── .env                        # משתני סביבה וחיבור ל-MongoDB Atlas
├── config/
│   ├── __init__.py
│   └── settings.py             # ניהול הגדרות מערכת ופרמטרים של המודל
├── models/
│   ├── __init__.py
│   └── detection_schema.py     # סכמות Pydantic לקלט/פלט מובנה
├── dal/                        # Data Access Layer
│   ├── __init__.py
│   └── detection_repo.py       # פעולות CRUD מול MongoDB Atlas
├── agents/                     # Agno Multi-Agent Team
│   ├── __init__.py
│   ├── vision_agent.py         # סוכן 1: פענוח תמונה ו-OCR
│   ├── knowledge_agent.py      # סוכן 2: בדיקת היסטוריה ב-DB והעשרת מידע
│   └── orchestrator_team.py    # סוכן מתזמר (Orchestrator Pattern)
├── services/                   # Business Logic Layer (BLL)
│   ├── __init__.py
│   ├── recognition_service.py  # תיאום בין ה-Orchestrator לשכבת ה-DAL
│   └── camera_service.py       # ניהול זרם הווידאו ב-OpenCV ותצוגת HUD
├── controllers/                # Presentation / API Layer
│   ├── __init__.py
│   └── api_controller.py       # Endpoints של Flask REST API
├── frontend/                   # Next.js 14 Web Application
│   ├── Dockerfile              # Multi-stage production container
│   ├── app/                    # App Router (page.tsx, layout.tsx, globals.css)
│   ├── components/             # UI Components (WebcamHUD, LatestAnalysis, History, Stats)
│   └── lib/                    # API client layer (api.ts)
├── Dockerfile                  # Python Backend & Multi-Agent container
├── docker-compose.yml          # תזמור מלא לשני השירותים
├── PRD.md
├── SPEC.md
├── PLAN.md
├── run_system.bat              # הפעלת שרת ופרונט מקומית
└── main.py                     # נקודת כניסה ראשית (הרצת שרת + מצלמה)
```

## 2.3 Environment & Database Config (`.env` & `config/settings.py`)
```env
MONGO_URI=mongodb+srv://idankzm:idankzm2468@cluster0.purdk.mongodb.net/?retryWrites=true&w=majority
DB_NAME=vision_agents_db
COLLECTION_NAME=detections
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
MODEL_ID=gemini-2.5-flash
CAMERA_INDEX=0
```

## 2.4 Data Schemas (`models/detection_schema.py`)
- **`VisionAnalysisResult(BaseModel)`**:
  - `object_name: str` (שם האובייקט המרכזי שזוהה)
  - `category: str` (קטגוריה של הפריט)
  - `detected_text: Optional[str] = None` (טקסט שנקרא ב-OCR)
  - `confidence: float` (`ge=0.0, le=1.0`)
  - `visual_description: str` (תיאור ויזואלי קצר)
- **`DetectionRecord(VisionAnalysisResult)`**:
  - `enrichment_summary: str` (תובנות מסוכן הידע וההיסטוריה מ-MongoDB)
  - `timestamp: datetime` (חותמת זמן UTC אוטומטית)

## 2.5 Layer Specifications

### A. Data Access Layer (`dal/detection_repo.py`)
- Connect to `settings.MONGO_URI` using `MongoClient`.
- `save_detection(record: DetectionRecord) -> str`: Insert `record.model_dump()` into `vision_agents_db.detections`.
- `get_recent_detections(limit: int = 20) -> List[Dict[str, Any]]`: Return latest records sorted by `timestamp` descending (`{"_id": 0}`).
- `find_by_object_name(object_name: str) -> List[Dict[str, Any]]`: Case-insensitive regex query on `object_name` limited to 3 recent records to prevent Context Overflow.

### B. Multi-Agent Layer (`agents/`)
1. **`agents/vision_agent.py` (`VisionPerceptionAgent`)**:
   - Uses `Agent` from `agno.agent` with `Gemini(id=settings.MODEL_ID, api_key=settings.GEMINI_API_KEY)`.
   - Configured with `response_model=VisionAnalysisResult`.
   - Method `analyze_frame(image_path: str) -> VisionAnalysisResult` passes `images=[Image(filepath=Path(image_path))]`.
2. **`agents/knowledge_agent.py` (`KnowledgeEnrichmentAgent`)**:
   - Defines tool function `check_detection_history(object_name: str) -> str` calling `detection_repo.find_by_object_name(object_name)`.
   - Agent instructions: Check if the item was previously scanned in MongoDB and return a concise 2-3 sentence enrichment summary in Hebrew.
3. **`agents/orchestrator_team.py` (`MultiAgentOrchestrator`)**:
   - Method `process_camera_frame(image_path: str) -> DetectionRecord`:
     1. Calls `vision_agent.analyze_frame(image_path)`.
     2. Calls `knowledge_agent.enrich(...)` with the vision output.
     3. Returns a complete `DetectionRecord` instance.

### C. Business Logic Layer (`services/`)
1. **`services/recognition_service.py` (`RecognitionService`)**:
   - Method `analyze_and_store(frame_path: str) -> DetectionRecord`: Calls `orchestrator.process_camera_frame(frame_path)` and saves the result via `detection_repo.save_detection(record)`.
2. **`services/camera_service.py` (`CameraService`)**:
   - Opens webcam via `cv2.VideoCapture(settings.CAMERA_INDEX)`.
   - Draws an overlay HUD bar at the top of the frame displaying current status/last detection.
   - Pressing `SPACE` saves the frame to `settings.TEMP_FRAME_PATH` and triggers `recognition_service.analyze_and_store()`.
   - Pressing `q` releases the camera and closes OpenCV windows cleanly.

### D. API Controller & Entrypoint (`controllers/api_controller.py` & `main.py`)
- `GET /api/detections`: Returns JSON list of recent detections from `detection_repo.get_recent_detections()`.
- `GET /api/detections/search`: Filters detections by query param `?q=<object_name>`.
- `main.py`: Runs the Flask app in a background daemon thread (`127.0.0.1:5000`) and starts `camera_service.start_stream()` on the main thread.
