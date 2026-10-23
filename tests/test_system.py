import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from main import create_app
from models.detection_schema import DetectionRecord, VisionAnalysisResult
from services.guardrails_service import guardrails_service
from services.mcp_server_service import mcp_server_service
from services.telemetry_service import telemetry_service

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test health check endpoint schema and status code."""
    res = client.get("/api/health")
    assert res.status_code in (200, 503)
    data = res.get_json()
    assert "status" in data
    assert "features" in data
    assert data["features"]["gemini_vision"] is True
    assert data["features"]["mcp_server"] is True
    assert data["features"]["ai_guardrails"] is True

def test_guardrails_pii_redaction():
    """Verify AI Guardrails redacts sensitive Israeli phone numbers and emails."""
    record = DetectionRecord(
        object_name="Visiting Card",
        category="Stationery",
        confidence=0.92,
        visual_description="A business card with contact details",
        enrichment_summary="כרטיס ביקור",
        detected_text="Contact me at 054-1234567 or support@example.com"
    )
    result = guardrails_service.apply_guardrails(record)
    assert "pii_redacted" in result["flags"]
    assert "[REDACTED_PHONE]" in record.detected_text
    assert "[REDACTED_EMAIL]" in record.detected_text

def test_guardrails_confidence_threshold():
    """Verify AI Guardrails flags low-confidence recognitions."""
    record = DetectionRecord(
        object_name="Blurry Object",
        category="Unknown",
        confidence=0.45,
        visual_description="Blurry frame",
        enrichment_summary="זיהוי בוודאות נמוכה"
    )
    result = guardrails_service.apply_guardrails(record)
    assert result["human_verification_required"] is True
    assert "low_confidence_warning" in result["flags"]

def test_mcp_server_tools_list():
    """Verify Model Context Protocol (MCP) tools/list conforms to specification."""
    rpc_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    response = mcp_server_service.handle_json_rpc(rpc_request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "tools" in response["result"]
    tools = {t["name"] for t in response["result"]["tools"]}
    assert "get_latest_detection" in tools
    assert "search_visual_memory" in tools
    assert "get_system_telemetry" in tools

def test_telemetry_cost_calculations():
    """Verify context token accounting and cost conversions in USD and ILS."""
    telemetry_service.record_scan_metrics(duration_seconds=1.2, prompt_tokens=500, completion_tokens=200)
    summary = telemetry_service.get_summary_metrics()
    assert summary["total_scans"] >= 1
    assert "estimated_cost_usd" in summary
    assert "estimated_cost_ils" in summary
    assert summary["estimated_cost_ils"].startswith("₪")

def test_detection_schema_pydantic():
    """Verify Pydantic model serialization and validation."""
    result = VisionAnalysisResult(
        object_name="Smartphone",
        category="Electronics",
        detected_entities=["Phone", "Screen"],
        face_detected=False,
        hands_detected=True,
        confidence=0.98,
        visual_description="Modern smartphone held by hand"
    )
    assert result.confidence == 0.98
    assert result.hands_detected is True
    dump = result.model_dump()
    assert dump["object_name"] == "Smartphone"
