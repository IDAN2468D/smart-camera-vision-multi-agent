# 🚀 דוח ביקורת (Feature Audit), השוואת אתרים ומפת דרכים: Smart Camera Vision Multi-Agent (v3.0 SDD)

מסמך זה מרכז ביקורת קוד מלאה (Gap Analysis) על מערכת **Smart Camera Vision Recognition Multi-Agent (v2.0)** הקיימת בקוד המקור, השוואה מול פלטפורמות ומוצרי Computer Vision מובילים בעולם, הצעות לשדרוג הפיצ'רים הקיימים (סגירת פערי v2.0), ופיצ'רים חדשים לחלוטין לדור הבא (**v3.0**) בהתאם לסטנדרט **Specification-Driven Development (SDD)**, רינדור **120Hz Zero-Reflow GPU**, סאונד מרחבי ב-**Web Audio API (`PannerNode`)**, ותמיכה מלאה בעברית (**RTL**) ובשקלים (**₪**).

---

## 🔍 חלק 1: ביקורת מצב קיים בקוד (Codebase Audit — v2.0 Reality vs. Spec)

לאחר סריקת כלל קבצי הפרויקט (`frontend/`, `agents/`, `services/`, `controllers/`, `dal/`, `models/`) מול מסמך `ROADMAP_V2.md`, זוהו הפערים ההנדסיים הבאים שדורשים שדרוג מיידי:

| רכיב בקוד הנוכחי | מה קיים בפועל בקוד (v2.0) | הפער ההנדסי שזוהה (Gap Analysis) | כיוון השדרוג המוצע |
| :--- | :--- | :--- | :--- |
| **`WebcamHUD.tsx` & `package.json`** | כפתור ידני `Thumbs-Up 👍` שמדמה מחווה (`triggerScan("gesture_thumbs_up")`), ומסגרת רטיקל סטטית ב-CSS ללא Canvas חי. | ספריית `@mediapipe/tasks-vision` אינה מותקנת ב-`package.json`. אין זיהוי 21 מפרקי יד אמיתי מהמצלמה, ואין ציור Bounding Boxes דינמיים על גבי הווידאו. | שילוב [MediaPipe HandLandmarker & ObjectDetector](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/web_js) ב-WebGPU עם שכבת `<canvas>` חיה ב-60/120FPS וטבעת טעינה של `800ms` לזיהוי מחוות אמיתי ללא מגע. |
| **`agents/commerce_agent.py`** | הסוכן `CommercePriceAgent` מאותחל ללא כלים חיצוניים (`tools` לא מועבר ל-`Agent`) ומסתמך על זיכרון המודל בלבד. | מחירי המוצרים בשקלים (`₪`) ושדה `source_url` מבוססים על הערכה פנימית של ה-LLM ולא על נתוני שוק בזמן אמת, ולעיתים חסרים קישור אמיתי. | חיבור [Agno TavilyTools](https://docs.agno.com/tools/toolkits/search/tavily) ו-[DuckDuckGoTools](https://docs.agno.com/examples/tools/duckduckgo-tools) לחיפוש חי בחנויות בישראל, חילוץ מחיר עדכני ב-`₪`, והשוואת מפרטים עם קישור מאומת. |
| **`api_controller.py` (`/api/faces/enroll`)** | נקודת הקצה שומרת רק `{"name": name, "role": role}` באוסף `known_faces` ב-MongoDB ללא עיבוד תמונה. | לא מתבצע חילוץ וקטור פנים (Face Embedding 512D), וה-Orchestrator אינו משווה פנים מול `known_faces` כדי לאכלס את `recognized_person_name`. | שילוב [InsightFace](https://github.com/deepinsight/insightface) או [DeepFace](https://github.com/serengil/deepface) לחילוץ וקטור פנים ביומטרי (512D ArcFace), שמירתו ב-Atlas Vector Search וזיהוי אוטומטי של המשתמש ב-HUD וב-TTS. |
| **`services/telemetry_service.py`** | הפונקציה `record_scan_metrics` מקבלת ערכי ברירת מחדל קבועים (`prompt_tokens=450, completion_tokens=180`). | חישוב העלות (`₪0.0012`) אינו קורא את ה-Usage Metadata האמיתי שחוזר מתגובת ה-API של Gemini בכל קריאת סוכן. | חילוץ מדויק של `usage_metadata.prompt_token_count` ו-`candidates_token_count` מכל סוכן ב-Agno ושילוב מעקב Traces מלא ב-[Langfuse](https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse) או [Arize Phoenix](https://github.com/arize-ai/phoenix). |
| **`services/export_service.py`** | ייצוא ה-PDF משתמש בפונט `Helvetica-Bold` ב-ReportLab וללא הטמעת תמונות ה-WebP (`thumbnail_base64`). | טקסט בעברית (`enrichment_summary`) עלול להופיע הפוך או כריבועים ב-PDF ללא פונט עברי ו-BiDi, והדוח חסר את תמונות ה-Snapshot שנסרקו. | רינדור דוח PDF תומך RTL מלא (באמצעות פונט עברי מוטמע ו-BiDi או HTML-to-PDF) הכולל את תמונת ה-Thumbnail של כל זיהוי, גרף התפלגות קטגוריות וסיכום עלויות ב-`₪`. |
| **`LatestAnalysis.tsx` & `voice_service.py`** | ניגון אודיו מונו/סטריאו רגיל בתגית `<audio>` ללא מיקום מרחבי וללא שיחה דו-כיוונית. | חסר משוב אקוסטי מרחבי (Spatial Audio) שממקם את הסאונד לפי מיקום האובייקט בפריים, ואין אפשרות לשאול את הסוכן שאלות המשך בקול. | הוספת [Web Audio API `PannerNode`](https://developer.mozilla.org/en-US/docs/Web/API/PannerNode) שממפה את קואורדינטות ה-Bounding Box (`x_min, x_max`) לבמה תלת-ממדית, פלוס מצב שיחה דו-כיווני חי ב-[Gemini Live API](https://ai.google.dev/gemini-api/docs/live-api). |

---

## 🌐 חלק 2: השראה ודוגמאות מאתרים ופלטפורמות מובילות בעולם

1. **[Frigate NVR](https://frigate.video/) & [Roboflow Supervision](https://supervision.roboflow.com/latest/notebooks/occupancy_analytics/) — אזורי עניין חכמים (Polygon Zones), מעקב מסלול (ByteTrack) וזמן שהייה (Dwell Time)**
2. **[Amazon Lens Live](https://www.retaildive.com/news/amazon-lens-visual-search-ai-shopping-assistant/759421/) & [Google Lens Shopping](https://blog.google/products-and-platforms/products/shopping/visual-search-lens-shopping/) — זיהוי רב-מוצרי חי והשוואת מחירים אינטראקטיבית**
3. **[Voxel51 FiftyOne](https://voxel51.com/) — Active Learning, גילוי אנומליות ומפת Embeddings תלת-ממדית**
4. **[Google AI Studio — Gemini Live API](https://aistudio.google.com/docs/live-api) — שיחה קולית וחזותית דו-כיוונית בזמן אמת (WebRTC / WebSockets)**
5. **[Hugging Face Transformers.js](https://huggingface.co/docs/transformers.js/en/index) & [ONNX Runtime Web](https://onnxruntime.ai/docs/get-started/with-javascript/web.html) — הרצת מודלי Edge Vision בדפדפן על WebGPU**

---

## 📊 חלק 3: מטריצת מפת דרכים (Feature Roadmap Matrix — v2.5 Upgrades & v3.0 New Features)

| Feature Name | Target Sprint | PRD/SPEC Ready | Tech Stack/API |
| :--- | :---: | :---: | :--- |
| **1. WebGPU Real-Time HUD & Zero-Touch Gestures** (שדרוג `WebcamHUD`) | Sprint 5 (v2.5) | ✅ Ready | `@mediapipe/tasks-vision`, HTML5 `<canvas>`, `transform-gpu` (120Hz Zero-Reflow) |
| **2. Live Israeli Commerce & Multi-Product Hotspots** (שדרוג `CommercePriceAgent`) | Sprint 5 (v2.5) | ✅ Ready | `agno.tools.duckduckgo` / search API, Pydantic `List[ProductPriceInfo]` (`₪`) |
| **3. Active Learning Few-Shot Loop & Telemetry** (שדרוג `guardrails_service` & `telemetry`) | Sprint 6 (v2.5) | ✅ Ready | Vector memory HITL few-shot injection, dynamic token accounting |
| **4. Acoustic Wavefront 3D Spatial Audio Feedback** (פיצ'ר חדש v3.0) | Sprint 7 (v3.0) | ✅ Ready | Web Audio API (`AudioContext`, `PannerNode` HRTF, `BiquadFilterNode`), `edge-tts` |
| **5. Interactive Polygon Zones, Dwell Time & Temporal Diff** (פיצ'ר חדש v3.0) | Sprint 7 (v3.0) | ✅ Ready | `SceneDeltaReport`, temporal frame comparison, SSE Alert Bus |
| **6. Bidirectional Voice & Vision Assistant ("Ask Camera Live")** (פיצ'ר חדש v3.0) | Sprint 8 (v3.0) | ✅ Ready | `POST /api/ask`, Gemini Flash Vision + Conversational Agent |
| **7. Multi-Object Comparison & Visual Diff Studio** (פיצ'ר חדש v3.0) | Sprint 8 (v3.0) | ✅ Ready | `POST /api/compare`, `CompareView.tsx`, Side-by-Side Spec Matrix (`₪`) |
