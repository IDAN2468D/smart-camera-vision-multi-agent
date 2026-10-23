# 🗓️ PLAN: Implementation Roadmap

## Phase 1: Project Scaffolding & Environment Setup
- [x] Create project root and subdirectories (`config`, `models`, `dal`, `agents`, `services`, `controllers`) using `cmd /c`.
- [x] Create Python virtual environment and install dependencies (`agno`, `google-genai`, `opencv-python`, `flask`, `pymongo`, `dnspython`, `pydantic`, `python-dotenv`, `pillow`) using `cmd /c`.
- [x] Create `.env` with the MongoDB Atlas URI and implement `config/settings.py`.

## Phase 2: Data Schemas & MongoDB DAL
- [x] Implement `models/detection_schema.py` with `VisionAnalysisResult` and `DetectionRecord`.
- [x] Implement `dal/detection_repo.py` and verify connection to `cluster0.purdk.mongodb.net`.

## Phase 3: Agno Multi-Agent Implementation
- [x] Implement `agents/vision_agent.py` for structured image & OCR analysis.
- [x] Implement `agents/knowledge_agent.py` with the `check_detection_history` MongoDB tool.
- [x] Implement `agents/orchestrator_team.py` to coordinate both agents.

## Phase 4: Services (BLL), Camera Loop & Flask API
- [x] Implement `services/recognition_service.py` and `services/camera_service.py`.
- [x] Implement `controllers/api_controller.py` with `/api/detections` and `/api/detections/search`.
- [x] Implement `main.py` combining the background Flask server and main OpenCV thread.

## Phase 5: End-to-End Verification
- [x] Run the system using `cmd /c venv\Scripts\python main.py` / `test_system.py`.
- [x] Scan an object using `SPACE` and verify document creation in MongoDB Atlas (`vision_agents_db.detections`).
- [x] Scan the same object a second time to verify `KnowledgeEnrichmentAgent` retrieves its history from MongoDB.
- [x] Test `http://127.0.0.1:5000/api/detections` in the browser or Postman.
