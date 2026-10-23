import sys
import threading
import logging

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from flask import Flask
from config.settings import settings
from controllers.api_controller import api_blueprint
from services.camera_service import camera_service

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("main")

def create_app() -> Flask:
    """Create and configure Flask application instance."""
    app = Flask(__name__)
    app.register_blueprint(api_blueprint)
    
    @app.after_request
    def after_request(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return response

    @app.route("/")
    def index():
        from flask import render_template_string
        html = """
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
            <meta charset="utf-8">
            <title>Vision AI Multi-Agent Backend</title>
            <style>
                body { font-family: system-ui, -apple-system, sans-serif; background: #070b14; color: #f8fafc; padding: 40px; text-align: center; }
                .card { max-width: 600px; margin: 0 auto; background: #0f172a; border: 1px solid #0ea5e9; border-radius: 16px; padding: 30px; box-shadow: 0 10px 30px rgba(14,165,233,0.2); }
                h1 { color: #38bdf8; font-size: 24px; margin-bottom: 10px; }
                p { color: #94a3b8; line-height: 1.6; }
                .badge { display: inline-block; background: rgba(16,185,129,0.2); color: #34d399; padding: 6px 14px; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }
                .btn-group { display: flex; gap: 10px; justify-content: center; margin-top: 20px; flex-wrap: wrap; }
                a.btn { display: inline-block; background: #0ea5e9; color: #ffffff; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: bold; transition: all 0.2s; }
                a.btn:hover { background: #38bdf8; }
                a.btn-secondary { background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; }
                a.btn-secondary:hover { background: #334155; }
                .endpoints { text-align: left; background: #020617; padding: 15px; border-radius: 8px; margin-top: 20px; font-family: monospace; font-size: 13px; color: #cbd5e1; direction: ltr; }
            </style>
        </head>
        <body>
            <div class="card">
                <span class="badge">● שרת ה-Backend וה-Orchestrator פעיל (Port 5000 / 5005)</span>
                <h1>🚀 Smart Vision AI Multi-Agent API</h1>
                <p>שרת ה-API והסוכנים פועל ומשרת את אפליקציית ה-Frontend.</p>
                <div class="btn-group">
                    <a href="http://localhost:3002" class="btn">פתח את ממשק המצלמה (Port 3002)</a>
                    <a href="/api/docs" class="btn btn-secondary">פתח תיעוד Swagger (Docs)</a>
                </div>
                <div class="endpoints">
                    <strong>Primary API Endpoints:</strong><br>
                    - GET  /api/health<br>
                    - GET  /api/docs (Swagger UI)<br>
                    - GET  /api/detections<br>
                    - POST /api/analyze<br>
                    - GET  /api/stream (SSE)<br>
                    - GET  /api/export (Excel/PDF)<br>
                    - POST /api/mcp (Model Context Protocol)
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html), 200

    @app.route("/docs")
    def docs_redirect():
        from flask import redirect
        return redirect("/api/docs")
    
    return app

def run_flask_server(app: Flask):
    """Run Flask server on background daemon thread."""
    logger.info(f"Starting Flask server on http://{settings.FLASK_HOST}:{settings.FLASK_PORT}")
    try:
        app.run(
            host=settings.FLASK_HOST,
            port=settings.FLASK_PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Flask server terminated unexpectedly: {e}")

def main():
    """Main application entry point."""
    print("=" * 70)
    print("🚀 SMART CAMERA VISION RECOGNITION MULTI-AGENT SYSTEM")
    print(f"📦 Model: {settings.MODEL_ID} | Database: {settings.DB_NAME}")
    print("=" * 70)

    # 1. Initialize and start Flask REST API in daemon thread
    flask_app = create_app()
    flask_thread = threading.Thread(
        target=run_flask_server,
        args=(flask_app,),
        daemon=True,
        name="FlaskAPIThread"
    )
    flask_thread.start()

    # 2. Run OpenCV camera loop on the main thread
    try:
        camera_service.start_stream()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error in camera loop: {e}", exc_info=True)
    finally:
        print("\n👋 System shut down successfully. Goodbye!\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
