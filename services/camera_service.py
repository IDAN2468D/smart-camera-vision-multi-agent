import cv2
import time
import logging
import threading
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from typing import Optional
from pathlib import Path
from config.settings import settings
from models.detection_schema import DetectionRecord
from services.recognition_service import recognition_service

logger = logging.getLogger(__name__)

class CameraService:
    """Manages OpenCV live camera feed, Heads-Up Display (HUD) overlay, and capture triggers."""

    def __init__(self):
        self.camera_index = settings.CAMERA_INDEX
        self.temp_frame_path = Path(settings.TEMP_FRAME_PATH)
        self.is_running = False
        self.is_analyzing = False
        self.auto_scan = False
        self.last_auto_scan_time = 0.0
        self.last_record: Optional[DetectionRecord] = None
        self.status_message = "Ready. Press [SPACE] to Scan, [A] for Auto-Scan, [Q] to Quit."
        self.current_fps = 0.0
        self._fps_counter = 0
        self._fps_start_time = time.time()
        self._lock = threading.Lock()

    def _draw_hud(self, frame):
        """Render an expanded modern HUD bar overlay on top of the OpenCV camera frame."""
        h, w, _ = frame.shape

        # Semi-transparent HUD header background (expanded for multi-entity info)
        overlay = frame.copy()
        hud_height = 110
        cv2.rectangle(overlay, (0, 0), (w, hud_height), (20, 20, 20), -1)
        
        # Bottom status bar background
        bottom_bar_height = 35
        cv2.rectangle(overlay, (0, h - bottom_bar_height), (w, h), (15, 15, 15), -1)
        
        # Apply transparency alpha blend
        alpha = 0.80
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Draw HUD border lines
        cv2.line(frame, (0, hud_height), (w, hud_height), (0, 200, 255), 2)
        cv2.line(frame, (0, h - bottom_bar_height), (w, h - bottom_bar_height), (100, 100, 100), 1)

        # Header Title and Mode Indicator
        auto_mode_str = "[AUTO-SCAN: ACTIVE (8s)]" if self.auto_scan else "[AUTO-SCAN: OFF (Press A)]"
        auto_color = (50, 255, 120) if self.auto_scan else (180, 180, 180)
        cv2.putText(frame, f"SMART VISION HUD | FPS: {self.current_fps:.1f} [{settings.MODEL_ID}]", (15, 25),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 230, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, auto_mode_str, (w - 290, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, auto_color, 1, cv2.LINE_AA)

        # Detection Info
        with self._lock:
            if self.is_analyzing:
                status_text = "STATUS: [ANALYZING FACES, HANDS & OBJECTS VIA AGENTS...]"
                cv2.putText(frame, status_text, (15, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 165, 255), 2, cv2.LINE_AA)
            elif self.last_record:
                rec = self.last_record
                line1 = f"Focus: {rec.object_name} [{rec.category}] | Conf: {rec.confidence * 100:.1f}%"
                cv2.putText(frame, line1, (15, 48),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 255, 120), 1, cv2.LINE_AA)
                
                face_str = "YES" if rec.face_detected else "NO"
                hands_str = "YES" if rec.hands_detected else "NO"
                entities_str = ", ".join(rec.detected_entities) if rec.detected_entities else rec.object_name
                line2 = f"Face: {face_str} | Hands: {hands_str} | Items: {entities_str}"
                cv2.putText(frame, line2[:80], (15, 72),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.46, (240, 200, 50), 1, cv2.LINE_AA)

                ocr_info = f"OCR: {rec.detected_text or 'None'}"
                cv2.putText(frame, ocr_info[:80], (15, 96),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.43, (200, 200, 200), 1, cv2.LINE_AA)
            else:
                cv2.putText(frame, "Show your face, hands or hold an object and press [SPACE] (or [A] for Auto-Scan).", (15, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

            # Bottom instruction bar
            cv2.putText(frame, self.status_message, (15, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)

    def _async_process_frame(self, frame_to_save):
        """Background thread handler for analyzing captured frame without freezing OpenCV window."""
        try:
            with self._lock:
                self.is_analyzing = True
                self.status_message = "Analyzing frame with Gemini & Knowledge Agent..."

            # Save the frame to temp file
            self.temp_frame_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(self.temp_frame_path), frame_to_save)
            logger.info(f"Frame saved to {self.temp_frame_path}. Invoking recognition service...")

            # Run Recognition Service pipeline
            record = recognition_service.analyze_and_store(str(self.temp_frame_path))

            with self._lock:
                self.last_record = record
                self.status_message = f"Done: {record.object_name} ({record.category}) saved to MongoDB. Press [SPACE] to Scan, [A] for Auto-Scan."
            
            entities_txt = ", ".join(record.detected_entities) if record.detected_entities else record.object_name
            print("\n" + "=" * 65)
            print(f"🎯 DETECTION COMPLETED: {record.object_name} [{record.category}]")
            print(f"👤 Face Detected: {'YES' if record.face_detected else 'NO'} | ✋ Hands Detected: {'YES' if record.hands_detected else 'NO'}")
            print(f"🏷️ All Entities Identified: {entities_txt}")
            print(f"📊 Confidence: {record.confidence * 100:.1f}%")
            print(f"🔤 Detected OCR: {record.detected_text or 'None'}")
            print(f"📝 Visual Description: {record.visual_description}")
            print(f"🧠 Enrichment Summary:\n{record.enrichment_summary}")
            print("=" * 65 + "\n")

        except Exception as e:
            logger.error(f"Error during async recognition: {e}", exc_info=True)
            with self._lock:
                self.status_message = f"Error: {str(e)[:50]}"
        finally:
            with self._lock:
                self.is_analyzing = False

    def _init_camera(self) -> cv2.VideoCapture:
        """Find and open the working camera with active video feed (auto-detecting index and backend)."""
        candidates = [self.camera_index] + [i for i in [1, 0, 2] if i != self.camera_index]
        backends = [cv2.CAP_MSMF, cv2.CAP_ANY, cv2.CAP_DSHOW]

        for idx in candidates:
            for backend in backends:
                cap = cv2.VideoCapture(idx, backend)
                if not cap.isOpened():
                    continue
                # Warm up and test reading frames to check if sensor produces real video (not solid black)
                time.sleep(0.1)
                ret, test_frame = False, None
                for _ in range(5):
                    ret, test_frame = cap.read()
                if ret and test_frame is not None and test_frame.mean() > 1.0:
                    logger.info(f"Connected to camera index {idx} with backend {backend} (mean brightness: {test_frame.mean():.1f})")
                    self.camera_index = idx
                    return cap
                cap.release()

        # Fallback to configured camera if no camera had brightness > 1
        return cv2.VideoCapture(self.camera_index)

    def start_stream(self):
        """Open the video capture stream and start the OpenCV event loop."""
        import os

        # Check for headless environment (e.g., inside Docker container or no GUI display)
        is_headless = os.environ.get("HEADLESS", "false").lower() == "true" or (
            sys.platform != "win32" and not os.environ.get("DISPLAY")
        )

        if is_headless:
            logger.info("Running in HEADLESS mode (Docker container). GUI window disabled. REST API active.")
            print("\n🚀 [HEADLESS MODE ACTIVE]: Running in headless Docker container environment.")
            print("The Flask REST API is live and serving the Next.js Web Frontend on port 5000.\n")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Headless service stopped by user.")
            return

        logger.info(f"Initializing camera stream (preferred index: {self.camera_index})...")
        cap = self._init_camera()

        if not cap.isOpened():
            logger.error(f"Could not open camera at index {self.camera_index}.")
            print(f"\n⚠️  [CAMERA WARNING]: Could not open webcam at index {self.camera_index}.")
            print("Make sure your webcam is plugged in and accessible.")
            print("The Flask REST API is still running on http://127.0.0.1:5000/api/detections.\n")
            return

        # Unlock High FPS (60 FPS) via MJPG Hardware Compression and minimal buffer
        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        except Exception:
            pass
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60.0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        window_name = "Smart Camera Vision Recognition - Multi-Agent System"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        self.is_running = True
        self._fps_counter = 0
        self._fps_start_time = time.time()

        print(f"\n🎥 High-FPS camera stream started successfully. Window: '{window_name}'.")
        print("⌨️  Controls: [SPACE] Manual Scan | [A] Toggle Auto-Scan (every 8s) | [Q] Quit.\n")

        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to grab video frame. Retrying...")
                    time.sleep(0.05)
                    continue

                # Calculate real-time FPS
                self._fps_counter += 1
                now = time.time()
                elapsed = now - self._fps_start_time
                if elapsed >= 1.0:
                    self.current_fps = self._fps_counter / elapsed
                    self._fps_counter = 0
                    self._fps_start_time = now

                # Auto-scan trigger (8s interval to respect Free Tier 15 RPM limit)
                if self.auto_scan and not self.is_analyzing:
                    if time.time() - self.last_auto_scan_time > 8.0:
                        self.last_auto_scan_time = time.time()
                        raw_frame = frame.copy()
                        worker = threading.Thread(
                            target=self._async_process_frame,
                            args=(raw_frame,),
                            daemon=True
                        )
                        worker.start()

                # Draw HUD
                self._draw_hud(frame)

                # Show frame
                cv2.imshow(window_name, frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q') or key == 27:  # ESC or Q
                    logger.info("Exit key pressed. Stopping camera stream.")
                    break
                elif key == ord('a') or key == ord('A'):  # Toggle Auto-scan
                    self.auto_scan = not self.auto_scan
                    state_msg = "ENABLED (Scanning every 4s)" if self.auto_scan else "DISABLED"
                    print(f"🔄 Auto-Scan mode: {state_msg}")
                    with self._lock:
                        self.status_message = f"Auto-Scan {state_msg}. Press [SPACE] for single scan, [A] to toggle."
                elif key == 32:  # SPACE key
                    if not self.is_analyzing:
                        # Copy clean frame (without HUD) for AI analysis
                        raw_frame = frame.copy()
                        # Launch analysis in worker thread
                        worker = threading.Thread(
                            target=self._async_process_frame,
                            args=(raw_frame,),
                            daemon=True
                        )
                        worker.start()
                    else:
                        print("⏳ Recognition is already in progress, please wait...")

        finally:
            self.is_running = False
            cap.release()
            cv2.destroyAllWindows()
            logger.info("Camera released and windows closed cleanly.")

camera_service = CameraService()
