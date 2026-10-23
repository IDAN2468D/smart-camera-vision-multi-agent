import os
import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import logging
from flask import Flask, request, jsonify, render_template_string
from services.mcp_server_service import mcp_server_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (mcp_microservice) %(message)s"
)
logger = logging.getLogger("mcp_microservice")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    html = """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="utf-8">
        <title>Vision MCP Server Microservice</title>
        <style>
            body { font-family: system-ui, -apple-system, sans-serif; background: #070b14; color: #f8fafc; padding: 40px; text-align: center; }
            .card { max-width: 600px; margin: 0 auto; background: #0f172a; border: 1px solid #8b5cf6; border-radius: 16px; padding: 30px; box-shadow: 0 10px 30px rgba(139,92,246,0.2); }
            h1 { color: #a78bfa; font-size: 24px; margin-bottom: 10px; }
            p { color: #94a3b8; line-height: 1.6; }
            .badge { display: inline-block; background: rgba(139,92,246,0.2); color: #c4b5fd; padding: 6px 14px; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }
            a.btn { display: inline-block; background: #8b5cf6; color: #ffffff; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-top: 20px; transition: all 0.2s; }
            a.btn:hover { background: #a78bfa; }
            .endpoints { text-align: left; background: #020617; padding: 15px; border-radius: 8px; margin-top: 20px; font-family: monospace; font-size: 13px; color: #cbd5e1; direction: ltr; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">● מיקרו-סרוויס MCP JSON-RPC 2.0 פעיל (Port 5002 / 5006)</span>
            <h1>🔌 Model Context Protocol (MCP) Server</h1>
            <p>שירות זה הוא שרת כלים בפרוטוקול MCP עבור כלי AI (כגון Cursor, Claude Code, Antigravity). הוא אינו אתר המשתמש הראשי.</p>
            <p><strong>כדי לגשת לאתר הראשי עם המצלמה, הזיהוי החי והממשק המלא:</strong></p>
            <a href="http://localhost:3002" class="btn">פתח את אתר המערכת הראשי (Port 3002)</a>
            <div class="endpoints">
                <strong>Available Endpoints:</strong><br>
                - GET  /health<br>
                - GET  /mcp (Tool list)<br>
                - POST /mcp (JSON-RPC 2.0: tools/list, tools/call)
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "mcp_json_rpc_microservice",
        "status": "online",
        "server_name": mcp_server_service.SERVER_NAME,
        "version": mcp_server_service.SERVER_VERSION
    }), 200

@app.route("/mcp", methods=["GET", "POST"])
def mcp():
    """Handle Model Context Protocol (MCP) JSON-RPC 2.0 requests."""
    if request.method == "GET":
        return jsonify({
            "status": "active",
            "server": mcp_server_service.SERVER_NAME,
            "version": mcp_server_service.SERVER_VERSION,
            "tools": mcp_server_service.list_tools()
        }), 200

    data = request.get_json(silent=True) or {}
    response = mcp_server_service.handle_json_rpc(data)
    return jsonify(response), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    logger.info(f"🚀 Starting MCP Protocol Microservice on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
