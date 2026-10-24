import base64
import json
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request, Response, render_template_string
from config.settings import settings
from dal.detection_repo import detection_repo
from services.recognition_service import recognition_service
from services.sse_service import sse_service
from services.export_service import export_service
from services.mcp_server_service import mcp_server_service
from services.guardrails_service import guardrails_service
from services.telemetry_service import telemetry_service
from services.embedding_client import embedding_client

logger = logging.getLogger(__name__)

api_blueprint = Blueprint("api", __name__, url_prefix="/api")

@api_blueprint.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for API, MongoDB connection, and enterprise syllabus features."""
    db_connected = detection_repo.ping()
    metrics = telemetry_service.get_summary_metrics()
    return jsonify({
        "status": "online" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "database_name": detection_repo.db_name,
        "collection_name": detection_repo.collection_name,
        "model_id": settings.MODEL_ID,
        "features": {
            "gemini_vision": True,
            "voice_agent_tts": True,
            "commerce_pricing": True,
            "sse_stream": True,
            "excel_pdf_export": True,
            "mcp_server": True,
            "visual_rag_vector_search": True,
            "ai_guardrails": True,
            "human_in_the_loop": True,
            "context_cost_engineering": True
        },
        "telemetry": metrics
    }), 200 if db_connected else 503

@api_blueprint.route("/analyze", methods=["POST", "OPTIONS"])
def analyze_frame_endpoint():
    """Analyze an uploaded frame (base64 image or file) via Multi-Agent pipeline."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("image")
        trigger_source = data.get("trigger_source", "web_hud")
        gesture_detected = data.get("gesture_detected")
        
        target_path = settings.BASE_DIR / "web_temp_frame.jpg"

        if image_b64:
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(image_b64)
            with open(target_path, "wb") as f:
                f.write(img_bytes)
        elif "file" in request.files:
            file = request.files["file"]
            file.save(str(target_path))
        else:
            return jsonify({
                "success": False,
                "message": "No image data provided. Send JSON with base64 'image' or multipart 'file'."
            }), 400

        # Execute multi-agent recognition pipeline, guardrails, and persist to MongoDB
        record = recognition_service.analyze_and_store(
            str(target_path),
            trigger_source=trigger_source,
            gesture_detected=gesture_detected
        )
        
        return jsonify({
            "success": True,
            "data": {
                "object_name": record.object_name,
                "category": record.category,
                "detected_entities": record.detected_entities,
                "face_detected": record.face_detected,
                "hands_detected": record.hands_detected,
                "detected_text": record.detected_text,
                "confidence": record.confidence,
                "visual_description": record.visual_description,
                "enrichment_summary": record.enrichment_summary,
                "timestamp": record.timestamp.isoformat(),
                "trigger_source": record.trigger_source,
                "gesture_detected": record.gesture_detected,
                "product_info": record.product_info.model_dump() if record.product_info else None,
                "thumbnail_base64": record.thumbnail_base64,
                "tts_audio_base64": record.tts_audio_base64
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in /api/analyze endpoint: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@api_blueprint.route("/stream", methods=["GET"])
def stream_events():
    """Server-Sent Events (SSE) stream endpoint for live real-time pipeline and detection updates."""
    response = Response(
        sse_service.event_stream(),
        mimetype="text/event-stream"
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@api_blueprint.route("/detections", methods=["GET"])
def get_detections():
    """Retrieve recent object detections."""
    limit = request.args.get("limit", default=20, type=int)
    detections = detection_repo.get_recent_detections(limit=limit)
    return jsonify({
        "success": True,
        "count": len(detections),
        "data": detections
    }), 200

@api_blueprint.route("/detections/search", methods=["GET"])
def search_detections():
    """Search detections by object name."""
    query = request.args.get("q", default="", type=str).strip()
    if not query:
        return jsonify({
            "success": False,
            "message": "Query parameter 'q' is required for search."
        }), 400

    matches = detection_repo.find_by_object_name(object_name=query, limit=10)
    return jsonify({
        "success": True,
        "query": query,
        "count": len(matches),
        "data": matches
    }), 200

@api_blueprint.route("/detections/similar", methods=["GET"])
def similar_detections():
    """Semantic (Visual RAG) search via the Embedding microservice: e.g. ?q=something to drink from"""
    query = request.args.get("q", default="", type=str).strip()
    limit = request.args.get("limit", default=5, type=int)
    min_score = request.args.get("min_score", default=0.0, type=float)
    if not query:
        return jsonify({
            "success": False,
            "message": "Query parameter 'q' is required for semantic search."
        }), 400

    try:
        result = embedding_client.search_similar(query=query, limit=limit, min_score=min_score)
        return jsonify({"success": True, "query": query, **result}), 200
    except Exception as e:
        logger.error(f"Semantic search failed: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@api_blueprint.route("/export", methods=["GET"])
def export_report():
    """Export detection records to Excel (.xlsx) or PDF (.pdf)."""
    fmt = request.args.get("format", default="excel", type=str).lower().strip()
    limit = request.args.get("limit", default=50, type=int)
    records = detection_repo.get_recent_detections(limit=limit)

    if fmt == "pdf":
        file_bytes = export_service.export_pdf(records)
        return Response(
            file_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=vision_detections_report.pdf"}
        )
    else:
        file_bytes = export_service.export_excel(records)
        return Response(
            file_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=vision_detections_report.xlsx"}
        )

@api_blueprint.route("/faces/enroll", methods=["POST"])
def enroll_face():
    """Enroll a recognized face profile into MongoDB Atlas."""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        role = data.get("role", "").strip()
        if not name:
            return jsonify({"success": False, "message": "Field 'name' is required"}), 400

        db = detection_repo.collection.database
        db["known_faces"].update_one(
            {"name": name},
            {"$set": {"name": name, "role": role, "updated_at": settings.MODEL_ID}},
            upsert=True
        )
        return jsonify({
            "success": True,
            "message": f"Face profile for '{name}' enrolled successfully."
        }), 200
    except Exception as e:
        logger.error(f"Failed to enroll face profile: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@api_blueprint.route("/mcp", methods=["POST", "GET"])
def mcp_endpoint():
    """Model Context Protocol (MCP) JSON-RPC 2.0 Endpoint.
    
    Allows external AI clients (Claude Desktop, Cursor, Antigravity) to connect
    and invoke Vision AI tools over standard MCP specification.
    """
    import os
    mcp_service_url = os.environ.get("MCP_SERVICE_URL")
    if mcp_service_url:
        try:
            import requests
            if request.method == "GET":
                res = requests.get(f"{mcp_service_url}/mcp", timeout=5)
                return jsonify(res.json()), res.status_code
            else:
                res = requests.post(
                    f"{mcp_service_url}/mcp",
                    json=request.get_json(silent=True) or {},
                    timeout=10
                )
                return jsonify(res.json()), res.status_code
        except Exception as e:
            logger.warning(f"MCP microservice proxy failed ({e}), falling back to internal handler.")

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

@api_blueprint.route("/detections/feedback", methods=["POST"])
def record_feedback():
    """Human-In-The-Loop (HITL) evaluation endpoint for human verification of agent output."""
    try:
        data = request.get_json(silent=True) or {}
        timestamp = data.get("timestamp")
        is_accurate = data.get("is_accurate", True)
        corrected_label = data.get("corrected_label")
        notes = data.get("notes")

        if not timestamp:
            return jsonify({"success": False, "message": "Timestamp required"}), 400

        success = guardrails_service.record_human_feedback(
            db_collection=detection_repo.collection,
            timestamp_iso=timestamp,
            is_accurate=is_accurate,
            corrected_label=corrected_label,
            notes=notes
        )
        telemetry_service.record_human_eval()
        return jsonify({"success": success, "message": "Feedback recorded."}), 200
    except Exception as e:
        logger.error(f"Feedback recording failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@api_blueprint.route("/metrics", methods=["GET"])
def get_metrics():
    """Context Engineering & Cost Accounting Metrics Endpoint."""
    return jsonify({
        "success": True,
        "metrics": telemetry_service.get_summary_metrics()
    }), 200

@api_blueprint.route("/docs", methods=["GET"])
def swagger_ui():
    """Interactive Swagger / OpenAPI 3.0 Documentation UI."""
    swagger_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vision AI Multi-Agent API - Swagger UI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
        <style>
            body { margin: 0; background: #0f172a; }
            .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
        <script>
            window.onload = () => {
                SwaggerUIBundle({
                    url: '/api/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [SwaggerUIBundle.presets.apis],
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(swagger_html)

@api_blueprint.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI 3.0 Specification."""
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "Smart Camera Vision Recognition Multi-Agent System",
            "version": "2.0.0",
            "description": "Production Multi-Agent Vision, Voice, Commerce & MCP API."
        },
        "paths": {
            "/api/health": {"get": {"summary": "Health check & telemetry"}},
            "/api/analyze": {"post": {"summary": "Analyze camera frame"}},
            "/api/stream": {"get": {"summary": "SSE real-time stream"}},
            "/api/detections": {"get": {"summary": "Recent detections"}},
            "/api/detections/similar": {"get": {"summary": "Semantic Visual RAG search (Atlas Vector Search)"}},
            "/api/export": {"get": {"summary": "Export PDF/Excel"}},
            "/api/mcp": {"post": {"summary": "Model Context Protocol JSON-RPC"}},
            "/api/detections/feedback": {"post": {"summary": "Human-In-The-Loop evaluation"}},
            "/api/metrics": {"get": {"summary": "Token & cost metrics"}}
        }
    })
