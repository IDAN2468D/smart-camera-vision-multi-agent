import os
import base64
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Backend-side client for the Embedding microservice.

    Calls the dedicated service when EMBEDDING_SERVICE_URL is set and transparently
    falls back to in-process execution (same decoupling pattern as VoiceService).
    """

    def __init__(self, embed_timeout: float = 15.0, search_timeout: float = 10.0):
        self.embed_timeout = embed_timeout
        self.search_timeout = search_timeout

    @property
    def service_url(self) -> Optional[str]:
        url = os.environ.get("EMBEDDING_SERVICE_URL")
        return url.rstrip("/") if url else None

    @staticmethod
    def _local():
        from services.embedding_service import embedding_service
        return embedding_service

    def _post(self, path: str, payload: Dict[str, Any], timeout: float) -> Optional[Dict[str, Any]]:
        url = self.service_url
        if not url:
            return None
        try:
            import requests
            res = requests.post(f"{url}{path}", json=payload, timeout=timeout)
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                return data
            logger.warning(f"Embedding microservice {path} returned {res.status_code}: {data.get('message')}")
        except Exception as e:
            logger.warning(f"Embedding microservice {path} call failed ({e}). Falling back to local execution.")
        return None

    def embed_frame(self, image_path: Optional[str], vision_result: Any) -> Optional[Dict[str, Any]]:
        """Create a multimodal embedding for a camera frame + its structured vision analysis."""
        text = self._local().build_document_text(vision_result)
        image_b64 = None
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

        remote = self._post("/embed", {"text": text, "image_base64": image_b64}, self.embed_timeout)
        if remote:
            return {"embedding": remote["embedding"], "model": remote["model"], "dimensions": remote["dimensions"]}

        try:
            return self._local().embed(text=text, image=image_b64)
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            return None

    def search_similar(
        self,
        query: Optional[str] = None,
        vector: Optional[List[float]] = None,
        model: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """Semantic similarity search over stored detections."""
        payload = {"query": query, "vector": vector, "model": model, "limit": limit, "min_score": min_score}
        remote = self._post("/search/similar", payload, self.search_timeout)
        if remote:
            return {k: remote[k] for k in ("data", "count", "model", "search_mode") if k in remote}

        return self._local().search_similar(query=query, vector=vector, model=model, limit=limit, min_score=min_score)

# Singleton client instance
embedding_client = EmbeddingClient()
