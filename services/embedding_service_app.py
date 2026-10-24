import os
import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import logging
from flask import Flask, request, jsonify, render_template_string
from services.embedding_service import embedding_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (embedding_microservice) %(message)s"
)
logger = logging.getLogger("embedding_microservice")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    html = """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="utf-8">
        <title>Visual RAG Embedding Microservice</title>
        <style>
            body { font-family: system-ui, -apple-system, sans-serif; background: #070b14; color: #f8fafc; padding: 40px; text-align: center; }
            .card { max-width: 600px; margin: 0 auto; background: #0f172a; border: 1px solid #10b981; border-radius: 16px; padding: 30px; box-shadow: 0 10px 30px rgba(16,185,129,0.2); }
            h1 { color: #34d399; font-size: 24px; margin-bottom: 10px; }
            p { color: #94a3b8; line-height: 1.6; }
            .badge { display: inline-block; background: rgba(16,185,129,0.2); color: #6ee7b7; padding: 6px 14px; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }
            a.btn { display: inline-block; background: #10b981; color: #070b14; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 20px; transition: all 0.2s; }
            a.btn:hover { background: #34d399; }
            .endpoints { text-align: left; background: #020617; padding: 15px; border-radius: 8px; margin-top: 20px; font-family: monospace; font-size: 13px; color: #cbd5e1; direction: ltr; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">● מיקרו-סרוויס Embeddings פעיל (Port 5003 / 5008)</span>
            <h1>🧠 Visual RAG Embedding Microservice</h1>
            <p>שירות זה מייצר וקטורי Embedding מולטימודליים (תמונה + טקסט) ומבצע חיפוש סמנטי ב-MongoDB Atlas Vector Search. הוא אינו אתר המשתמש הראשי.</p>
            <p><strong>כדי לגשת לאתר הראשי עם המצלמה, הזיהוי החי והממשק המלא:</strong></p>
            <a href="http://localhost:3002" class="btn">פתח את אתר המערכת הראשי (Port 3002)</a>
            <div class="endpoints">
                <strong>Available Endpoints:</strong><br>
                - GET  /health<br>
                - POST /embed (JSON: {"text": "...", "image_base64": "..."})<br>
                - POST /search/similar (JSON: {"query": "red mug", "limit": 5})<br>
                - POST /index/ensure (create Atlas vector index)<br>
                - POST /backfill (JSON: {"limit": 50})
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "visual_rag_embedding_microservice",
        "status": "online",
        "model": embedding_service.model,
        "dimensions": embedding_service.dimensions,
        "index_name": embedding_service.index_name,
        "mode": "gemini" if embedding_service.uses_remote_model else "local_fallback"
    }), 200

@app.route("/embed", methods=["POST"])
def embed():
    """Embed text and/or a base64 image into a single vector."""
    data = request.get_json(silent=True) or {}
    text = data.get("text") or ""
    image_b64 = data.get("image_base64")

    if not text.strip() and not image_b64:
        return jsonify({"success": False, "message": "Provide 'text' and/or 'image_base64'"}), 400

    try:
        result = embedding_service.embed(text=text, image=image_b64)
        return jsonify({"success": True, **result}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Embedding failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/search/similar", methods=["POST"])
def search_similar():
    """Semantic similarity search by free-text query or precomputed vector."""
    data = request.get_json(silent=True) or {}
    query = data.get("query")
    vector = data.get("vector")

    if not (query and str(query).strip()) and not vector:
        return jsonify({"success": False, "message": "Provide 'query' text or a precomputed 'vector'"}), 400
    if vector is not None and (not isinstance(vector, list) or len(vector) != embedding_service.dimensions):
        return jsonify({
            "success": False,
            "message": f"'vector' must be a list of {embedding_service.dimensions} floats"
        }), 400

    try:
        result = embedding_service.search_similar(
            query=query,
            vector=vector,
            model=data.get("model"),
            limit=int(data.get("limit", 5)),
            min_score=float(data.get("min_score", 0.0))
        )
        return jsonify({"success": True, **result}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Similarity search failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/index/ensure", methods=["POST"])
def ensure_index():
    """Create the Atlas Vector Search index if it does not exist."""
    try:
        return jsonify({"success": True, **embedding_service.ensure_index()}), 200
    except Exception as e:
        logger.error(f"Vector index creation failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/backfill", methods=["POST"])
def backfill():
    """Embed existing detections that are missing an embedding vector."""
    data = request.get_json(silent=True) or {}
    limit = max(1, min(int(data.get("limit", 50)), 500))
    try:
        return jsonify({"success": True, **embedding_service.backfill(limit=limit)}), 200
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    logger.info(f"🚀 Starting Visual RAG Embedding Microservice on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
