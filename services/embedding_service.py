import io
import re
import math
import base64
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union

from config.settings import settings
from dal.detection_repo import detection_repo, DetectionRepository

logger = logging.getLogger(__name__)

LOCAL_FALLBACK_MODEL = "local-hash-v1"

class EmbeddingService:
    """Visual RAG embedding engine.

    - Produces multimodal embeddings (frame image + structured vision text) with Gemini
      (`gemini-embedding-2` maps images and text into one shared vector space, so a
      free-text query can retrieve visually similar frames).
    - Falls back to a deterministic local feature-hashing embedding when no API key is
      configured or the remote call fails, so the pipeline never breaks.
    - Every vector is tagged with `embedding_model`, and searches are filtered by it,
      because vectors from different models are NOT comparable.
    """

    MAX_IMAGE_SIDE = 768

    def __init__(
        self,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        api_key: Optional[str] = None,
        repo: Optional[DetectionRepository] = None,
        index_name: Optional[str] = None
    ):
        self.model = model or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIM
        self.api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self.repo = repo or detection_repo
        self.index_name = index_name or settings.VECTOR_INDEX_NAME
        self._client = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def uses_remote_model(self) -> bool:
        """True when a real Gemini API key is configured."""
        return bool(self.api_key) and "YOUR_GEMINI_API_KEY" not in self.api_key and "your_gemini_api_key" not in self.api_key

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @staticmethod
    def _l2_normalize(vector: List[float]) -> List[float]:
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector] if norm > 0 else vector

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    @staticmethod
    def build_document_text(data: Union[Dict[str, Any], Any]) -> str:
        """Build a compact, embedding-friendly text from a vision result / detection record."""
        if not isinstance(data, dict):
            data = data.model_dump() if hasattr(data, "model_dump") else dict(data)

        parts: List[str] = []
        if data.get("object_name"):
            parts.append(f"Object: {data['object_name']}")
        if data.get("category"):
            parts.append(f"Category: {data['category']}")
        entities = data.get("detected_entities") or []
        if entities:
            parts.append(f"Entities: {', '.join(entities)}")
        product = data.get("product_info") or {}
        if isinstance(product, dict) and product.get("model_name"):
            parts.append(f"Product: {product['model_name']}")
        if data.get("detected_text"):
            parts.append(f"Text: {data['detected_text']}")
        if data.get("visual_description"):
            parts.append(f"Description: {data['visual_description']}")
        return ". ".join(parts)

    def prepare_image(self, image: Union[bytes, str, None]) -> Optional[bytes]:
        """Accept raw bytes, a base64 string or a data URI; return a downscaled JPEG (or None)."""
        if not image:
            return None
        try:
            if isinstance(image, str):
                if "," in image and image.strip().startswith("data:"):
                    image = image.split(",", 1)[1]
                image = base64.b64decode(image)

            from PIL import Image
            img = Image.open(io.BytesIO(image)).convert("RGB")
            img.thumbnail((self.MAX_IMAGE_SIDE, self.MAX_IMAGE_SIDE))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return buffer.getvalue()
        except Exception as e:
            logger.warning(f"Could not decode image for embedding, continuing text-only: {e}")
            return None

    def local_hash_embedding(self, text: str) -> List[float]:
        """Deterministic feature-hashing embedding (unigrams + bigrams), L2-normalized.

        Uses md5 (not Python's salted hash()) so vectors are stable across processes/containers.
        """
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.md5(feature.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[idx] += sign
        return self._l2_normalize(vector)

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _remote_embedding(self, text: str, image_bytes: Optional[bytes]) -> List[float]:
        from google.genai import types

        parts = []
        if text:
            parts.append(types.Part(text=text))
        if image_bytes:
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

        # One Content with several parts -> a single fused multimodal embedding
        response = self._get_client().models.embed_content(
            model=self.model,
            contents=types.Content(parts=parts),
            config=types.EmbedContentConfig(output_dimensionality=self.dimensions)
        )
        embeddings = [e.values for e in (response.embeddings or []) if e.values]
        if not embeddings:
            raise ValueError("Gemini returned no embedding values")
        if len(embeddings) == 1:
            vector = list(embeddings[0])
        else:  # Defensive: average if the API split parts into separate vectors
            vector = [sum(vals) / len(embeddings) for vals in zip(*embeddings)]
        # Truncated (Matryoshka) Gemini vectors must be re-normalized for cosine/dot similarity
        return self._l2_normalize(vector)

    def embed(self, text: str = "", image: Union[bytes, str, None] = None) -> Dict[str, Any]:
        """Embed text and/or an image.

        Returns:
            {"embedding": [...], "model": str, "dimensions": int, "modalities": [...]}
        """
        text = (text or "").strip()
        image_bytes = self.prepare_image(image)
        if not text and not image_bytes:
            raise ValueError("Nothing to embed: provide 'text' and/or a valid image")

        modalities = [m for m, present in (("text", bool(text)), ("image", bool(image_bytes))) if present]

        if self.uses_remote_model:
            try:
                vector = self._remote_embedding(text, image_bytes)
                return {"embedding": vector, "model": self.model, "dimensions": len(vector), "modalities": modalities}
            except Exception as e:
                logger.warning(f"Gemini embedding failed ({e}); falling back to local hashing embedding")

        if not text:
            raise ValueError("Local fallback embedding requires text (image-only input needs the Gemini model)")
        vector = self.local_hash_embedding(text)
        return {"embedding": vector, "model": LOCAL_FALLBACK_MODEL, "dimensions": len(vector), "modalities": ["text"]}

    # ------------------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------------------

    def _brute_force_search(self, vector: List[float], model: str, limit: int) -> List[Dict[str, Any]]:
        scored = []
        for doc in self.repo.find_with_embeddings(embedding_model=model):
            emb = doc.pop("image_embedding", None)
            score = self.cosine_similarity(vector, emb)
            # Map cosine [-1, 1] to [0, 1] to match Atlas' cosine vectorSearchScore scale
            doc["similarity_score"] = (1.0 + score) / 2.0
            scored.append(doc)
        scored.sort(key=lambda d: d["similarity_score"], reverse=True)
        return scored[:limit]

    def search_similar(
        self,
        query: Optional[str] = None,
        vector: Optional[List[float]] = None,
        model: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """Find semantically similar detections by free-text query or by a precomputed vector."""
        limit = max(1, min(int(limit or 5), 50))

        if vector is None:
            if not query or not query.strip():
                raise ValueError("Provide either 'query' text or a precomputed 'vector'")
            emb = self.embed(text=query)
            vector, model = emb["embedding"], emb["model"]
        model = model or self.model

        search_mode = "atlas_vector_search"
        try:
            results = self.repo.vector_search(vector, embedding_model=model, limit=limit, index_name=self.index_name)
            if not results:
                # Atlas returns [] (no error) while the index is missing/building -> verify with brute force
                results = self._brute_force_search(vector, model, limit)
                search_mode = "local_cosine_fallback" if results else search_mode
        except Exception as e:
            logger.info(f"$vectorSearch unavailable ({e}); using local cosine fallback")
            results = self._brute_force_search(vector, model, limit)
            search_mode = "local_cosine_fallback"

        results = [r for r in results if r.get("similarity_score", 0.0) >= min_score]
        return {"data": results, "count": len(results), "model": model, "search_mode": search_mode}

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def ensure_index(self) -> Dict[str, Any]:
        return self.repo.ensure_vector_index(dimensions=self.dimensions, index_name=self.index_name)

    def backfill(self, limit: int = 50) -> Dict[str, Any]:
        """Embed existing detections that were stored before the embedding service existed."""
        processed = updated = failed = 0
        for doc in self.repo.find_missing_embeddings(limit=limit):
            processed += 1
            try:
                emb = self.embed(text=self.build_document_text(doc), image=doc.get("thumbnail_base64"))
                if self.repo.set_embedding(doc["_id"], emb["embedding"], emb["model"]):
                    updated += 1
            except Exception as e:
                failed += 1
                logger.warning(f"Backfill failed for document {doc.get('_id')}: {e}")
        return {"processed": processed, "updated": updated, "failed": failed}

# Singleton service instance
embedding_service = EmbeddingService()
