import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from pymongo.errors import OperationFailure

from models.detection_schema import DetectionRecord, VisionAnalysisResult
from services.embedding_service import EmbeddingService, LOCAL_FALLBACK_MODEL
from services.embedding_client import EmbeddingClient

DIM = 768

class FakeRepo:
    """In-memory stand-in for DetectionRepository (no MongoDB needed)."""

    def __init__(self, docs=None, atlas_available=False):
        self.docs = docs or []
        self.atlas_available = atlas_available
        self.updated = {}

    def vector_search(self, query_vector, embedding_model, limit=5, index_name=None):
        if not self.atlas_available:
            raise OperationFailure("$vectorSearch is not allowed")
        return []

    def find_with_embeddings(self, embedding_model, limit=500):
        return [
            {k: v for k, v in d.items() if k != "_id"}
            for d in self.docs
            if d.get("embedding_model") == embedding_model and d.get("image_embedding")
        ]

    def find_missing_embeddings(self, limit=50):
        return [d for d in self.docs if not d.get("image_embedding")][:limit]

    def set_embedding(self, doc_id, vector, embedding_model):
        self.updated[doc_id] = (vector, embedding_model)
        return True

@pytest.fixture
def local_service():
    """EmbeddingService forced into offline local-hash mode."""
    return EmbeddingService(api_key="", dimensions=DIM, repo=FakeRepo())

def _doc(service, name, description):
    text = service.build_document_text({"object_name": name, "visual_description": description})
    return {
        "object_name": name,
        "visual_description": description,
        "image_embedding": service.local_hash_embedding(text),
        "embedding_model": LOCAL_FALLBACK_MODEL,
    }

def test_local_embedding_is_deterministic_and_normalized(local_service):
    a = local_service.local_hash_embedding("Red ceramic coffee mug")
    b = local_service.local_hash_embedding("Red ceramic coffee mug")
    assert a == b
    assert len(a) == DIM
    assert abs(sum(v * v for v in a) - 1.0) < 1e-9

def test_local_embedding_semantic_ordering(local_service):
    mug = local_service.local_hash_embedding("red ceramic coffee mug on desk")
    cup = local_service.local_hash_embedding("ceramic coffee mug with handle")
    phone = local_service.local_hash_embedding("black smartphone touch screen")
    assert local_service.cosine_similarity(mug, cup) > local_service.cosine_similarity(mug, phone)

def test_build_document_text_from_vision_result():
    result = VisionAnalysisResult(
        object_name="Smartphone",
        category="Electronics",
        detected_entities=["Phone", "Hand"],
        detected_text="iPhone",
        confidence=0.9,
        visual_description="A phone held in a hand"
    )
    text = EmbeddingService.build_document_text(result)
    assert "Object: Smartphone" in text
    assert "Entities: Phone, Hand" in text
    assert "Text: iPhone" in text

def test_embed_falls_back_to_local_without_api_key(local_service):
    out = local_service.embed(text="blue water bottle")
    assert out["model"] == LOCAL_FALLBACK_MODEL
    assert out["dimensions"] == DIM

def test_embed_requires_input(local_service):
    with pytest.raises(ValueError):
        local_service.embed(text="   ")

def test_search_uses_cosine_fallback_and_ranks(local_service):
    local_service.repo = FakeRepo(docs=[
        _doc(local_service, "Coffee Mug", "white ceramic coffee mug"),
        _doc(local_service, "Smartphone", "black phone with touch screen"),
        _doc(local_service, "Tea Cup", "ceramic cup for tea and coffee"),
    ])
    result = local_service.search_similar(query="ceramic coffee mug", limit=2)
    assert result["search_mode"] == "local_cosine_fallback"
    assert result["count"] == 2
    assert result["data"][0]["object_name"] == "Coffee Mug"
    assert "image_embedding" not in result["data"][0]
    assert 0.0 <= result["data"][0]["similarity_score"] <= 1.0

def test_search_filters_by_model_and_min_score(local_service):
    foreign = _doc(local_service, "Coffee Mug", "white ceramic coffee mug")
    foreign["embedding_model"] = "some-other-model"
    local_service.repo = FakeRepo(docs=[foreign])
    assert local_service.search_similar(query="coffee mug")["count"] == 0

    local_service.repo = FakeRepo(docs=[_doc(local_service, "Smartphone", "black phone")])
    assert local_service.search_similar(query="ceramic coffee mug", min_score=0.99)["count"] == 0

def test_backfill_embeds_missing_documents(local_service):
    local_service.repo = FakeRepo(docs=[
        {"_id": "a1", "object_name": "Laptop", "visual_description": "silver laptop"},
        {"_id": "a2", "object_name": "Pen", "visual_description": "blue pen", "image_embedding": [0.1] * DIM},
    ])
    stats = local_service.backfill(limit=10)
    assert stats == {"processed": 1, "updated": 1, "failed": 0}
    assert local_service.repo.updated["a1"][1] == LOCAL_FALLBACK_MODEL

def test_detection_record_carries_embedding_model():
    record = DetectionRecord(
        object_name="Mug", category="Drinkware", confidence=0.9,
        visual_description="mug", enrichment_summary="ספל",
        image_embedding=[0.0] * 4, embedding_model=LOCAL_FALLBACK_MODEL
    )
    dumped = record.model_dump(mode="json", exclude={"image_embedding"})
    assert dumped["embedding_model"] == LOCAL_FALLBACK_MODEL
    assert "image_embedding" not in dumped

def test_client_falls_back_to_local_when_service_unreachable(monkeypatch, local_service):
    import services.embedding_service as module
    monkeypatch.setattr(module, "embedding_service", local_service)
    monkeypatch.setenv("EMBEDDING_SERVICE_URL", "http://127.0.0.1:9")  # nothing listens here
    client = EmbeddingClient(embed_timeout=1, search_timeout=1)
    vision = VisionAnalysisResult(object_name="Mug", category="Drinkware", confidence=0.9, visual_description="red mug")
    out = client.embed_frame(image_path=None, vision_result=vision)
    assert out["model"] == LOCAL_FALLBACK_MODEL
    assert len(out["embedding"]) == DIM

# ---------------------------------------------------------------------------
# Microservice HTTP contract
# ---------------------------------------------------------------------------

@pytest.fixture
def micro_client(monkeypatch, local_service):
    import services.embedding_service_app as app_module
    monkeypatch.setattr(app_module, "embedding_service", local_service)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c

def test_microservice_health(micro_client):
    res = micro_client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "online"
    assert data["mode"] == "local_fallback"
    assert data["dimensions"] == DIM

def test_microservice_embed(micro_client):
    res = micro_client.post("/embed", json={"text": "green apple"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["embedding"]) == DIM

def test_microservice_embed_validation(micro_client):
    assert micro_client.post("/embed", json={}).status_code == 400

def test_microservice_search_validation(micro_client):
    assert micro_client.post("/search/similar", json={}).status_code == 400
    assert micro_client.post("/search/similar", json={"vector": [0.1, 0.2]}).status_code == 400

def test_microservice_search(micro_client, local_service):
    local_service.repo = FakeRepo(docs=[_doc(local_service, "Coffee Mug", "white ceramic coffee mug")])
    res = micro_client.post("/search/similar", json={"query": "coffee mug", "limit": 3})
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] == 1
    assert data["data"][0]["object_name"] == "Coffee Mug"
