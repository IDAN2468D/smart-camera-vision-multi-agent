import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from main import create_app
from services.scene_diff_service import scene_diff_service
from services.guardrails_service import guardrails_service
from models.detection_schema import VisionAnalysisResult, SpatialBoundingBox

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_scene_diff_service():
    """Verify temporal delta calculation and dwell time tracking."""
    v1 = VisionAnalysisResult(
        object_name="Smartphone",
        category="Electronics",
        detected_entities=["Smartphone", "Watch"],
        confidence=0.92,
        visual_description="A smartphone and smartwatch on a desk."
    )
    res1 = scene_diff_service.compute_delta(v1, zone_id="test_zone")
    assert "Smartphone" in res1.added_entities
    assert len(res1.removed_entities) == 0

    v2 = VisionAnalysisResult(
        object_name="Coffee Mug",
        category="Drinkware",
        detected_entities=["Coffee Mug"],
        confidence=0.95,
        visual_description="Smartphone removed, coffee mug added."
    )
    res2 = scene_diff_service.compute_delta(v2, zone_id="test_zone")
    assert "Coffee Mug" in res2.added_entities
    assert "Smartphone" in res2.removed_entities
    assert res2.dwell_time_seconds is not None

def test_few_shot_corrections_helper():
    """Verify few-shot active learning retrieval."""
    class DummyCollection:
        def find(self, *args, **kwargs):
            class DummyCursor:
                def limit(self, *args, **kwargs):
                    return [
                        {
                            "object_name": "Bowl",
                            "corrected_label": "Espresso Cup",
                            "visual_description": "Small ceramic cup on table"
                        },
                        {
                            "object_name": "Keyboard",
                            "corrected_label": "Mechanical Keyboard",
                            "visual_description": "RGB mechanical keyboard"
                        }
                    ]
            return DummyCursor()

    prompt_few_shots = guardrails_service.get_few_shot_corrections(DummyCollection(), limit=2)
    assert "Espresso Cup" in prompt_few_shots
    assert "Mechanical Keyboard" in prompt_few_shots

def test_api_ask_endpoint(client):
    """Verify /api/ask returns formatted AskVisionResponse."""
    payload = {
        "question_hebrew": "איזה צבע החפץ שביד שלי?"
    }
    resp = client.post("/api/ask", json=payload)
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["success"] is True
    assert "answer_hebrew" in json_data["data"]
    assert json_data["data"]["question_hebrew"] == "איזה צבע החפץ שביד שלי?"

def test_api_compare_endpoint(client):
    """Verify /api/compare returns structured comparison matrix with ILS pricing."""
    payload = {
        "label_a": "אוזניות Sony WH-1000XM5",
        "label_b": "אוזניות Bose QuietComfort Ultra"
    }
    resp = client.post("/api/compare", json=payload)
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["success"] is True
    assert "comparison_points" in json_data["data"]
    assert "winner_recommendation_hebrew" in json_data["data"]

def test_api_zones_diff_endpoint(client):
    """Verify /api/zones/diff runs delta computation."""
    resp = client.post("/api/zones/diff", json={"zone_id": "zone_lobby"})
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["success"] is True
    assert "delta" in json_data["data"]
    assert json_data["data"]["zone_id"] == "zone_lobby"
