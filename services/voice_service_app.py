import os
import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import logging
from flask import Flask, request, jsonify, render_template_string
from services.voice_service import voice_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (voice_microservice) %(message)s"
)
logger = logging.getLogger("voice_microservice")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    html = """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="utf-8">
        <title>Hebrew Voice TTS Microservice</title>
        <style>
            body { font-family: system-ui, -apple-system, sans-serif; background: #070b14; color: #f8fafc; padding: 40px; text-align: center; }
            .card { max-width: 600px; margin: 0 auto; background: #0f172a; border: 1px solid #06b6d4; border-radius: 16px; padding: 30px; box-shadow: 0 10px 30px rgba(6,182,212,0.2); }
            h1 { color: #38bdf8; font-size: 24px; margin-bottom: 10px; }
            p { color: #94a3b8; line-height: 1.6; }
            .badge { display: inline-block; background: rgba(16,185,129,0.2); color: #34d399; padding: 6px 14px; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }
            a.btn { display: inline-block; background: #06b6d4; color: #070b14; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 20px; transition: all 0.2s; }
            a.btn:hover { background: #38bdf8; }
            .endpoints { text-align: left; background: #020617; padding: 15px; border-radius: 8px; margin-top: 20px; font-family: monospace; font-size: 13px; color: #cbd5e1; direction: ltr; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">● מיקרו-סרוויס קולי פעיל (Port 5001 / 5007)</span>
            <h1>🔊 Hebrew Voice TTS Microservice</h1>
            <p>שירות זה הוא מיקרו-סרוויס עצמאי (Backend Microservice) האחראי על סינתזת קול בעברית טבעית (edge-tts). הוא אינו אתר המשתמש הראשי.</p>
            <p><strong>כדי לגשת לאתר הראשי עם המצלמה, הזיהוי החי והממשק המלא:</strong></p>
            <a href="http://localhost:3002" class="btn">פתח את אתר המערכת הראשי (Port 3002)</a>
            <div class="endpoints">
                <strong>Available Endpoints:</strong><br>
                - GET  /health<br>
                - POST /synthesize (JSON: {"text": "שלום"})
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "hebrew_voice_tts_microservice",
        "status": "online",
        "voice": voice_service.DEFAULT_VOICE
    }), 200

@app.route("/synthesize", methods=["POST"])
def synthesize():
    """Synthesize Hebrew text into Base64 MP3 audio."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    voice = data.get("voice")

    if not text:
        return jsonify({"success": False, "message": "Field 'text' is required"}), 400

    try:
        audio_b64 = voice_service.generate_speech(text=text, voice=voice)
        if not audio_b64:
            return jsonify({"success": False, "message": "TTS synthesis returned empty"}), 500

        return jsonify({
            "success": True,
            "audio_base64": audio_b64
        }), 200
    except Exception as e:
        logger.error(f"Error synthesizing speech in microservice: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"🚀 Starting Hebrew Voice TTS Microservice on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
