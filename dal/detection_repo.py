import logging
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from config.settings import settings
from models.detection_schema import DetectionRecord

logger = logging.getLogger(__name__)

# Projection used for all API/LLM-facing reads: hides Mongo '_id' and the large
# embedding vector (768+ floats) so it never bloats JSON responses or agent context.
PUBLIC_PROJECTION: Dict[str, int] = {"_id": 0, "image_embedding": 0}

def _normalize_timestamps(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert datetime 'timestamp' fields to ISO strings for JSON serialization."""
    for rec in records:
        if "timestamp" in rec and hasattr(rec["timestamp"], "isoformat"):
            rec["timestamp"] = rec["timestamp"].isoformat()
    return records

class DetectionRepository:
    """Data Access Layer (DAL) for managing detection records in MongoDB Atlas."""

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None, collection_name: Optional[str] = None):
        self.uri = uri or settings.MONGO_URI
        self.db_name = db_name or settings.DB_NAME
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None

    @property
    def collection(self) -> Collection:
        """Lazy-loading connection to MongoDB Atlas collection."""
        if self._collection is None:
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self._db = self._client[self.db_name]
            self._collection = self._db[self.collection_name]
        return self._collection

    def ping(self) -> bool:
        """Verify MongoDB Atlas connectivity."""
        try:
            self.collection.database.command("ping")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            return False

    def save_detection(self, record: DetectionRecord) -> str:
        """Insert a validated detection record into MongoDB Atlas.
        
        Args:
            record: Validated DetectionRecord instance.
            
        Returns:
            The inserted MongoDB Document ID as a string.
        """
        try:
            document = record.model_dump()
            result = self.collection.insert_one(document)
            inserted_id = str(result.inserted_id)
            logger.info(f"Successfully saved detection '{record.object_name}' with ID: {inserted_id}")
            return inserted_id
        except Exception as e:
            logger.error(f"Error saving detection to MongoDB: {e}")
            raise

    def get_recent_detections(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve the most recent detection records sorted descending by timestamp.
        
        Args:
            limit: Maximum number of records to return (default: 20).
            
        Returns:
            List of dictionaries representing detection records without '_id'.
        """
        try:
            cursor = self.collection.find({}, PUBLIC_PROJECTION).sort("timestamp", DESCENDING).limit(limit)
            records = list(cursor)
            # Normalize datetime to ISO string for JSON serialization
            for rec in records:
                if "timestamp" in rec and hasattr(rec["timestamp"], "isoformat"):
                    rec["timestamp"] = rec["timestamp"].isoformat()
            return records
        except Exception as e:
            logger.error(f"Error fetching recent detections from MongoDB: {e}")
            return []

    def find_by_object_name(self, object_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Perform a case-insensitive search by object name, limited to prevent context overflow.
        
        Args:
            object_name: The name or partial name of the object to search for.
            limit: Maximum number of historical records to retrieve (default: 3).
            
        Returns:
            List of matching records sorted by most recent first, without '_id'.
        """
        try:
            query = {"object_name": {"$regex": f"^{object_name.strip()}$", "$options": "i"}}
            cursor = self.collection.find(query, PUBLIC_PROJECTION).sort("timestamp", DESCENDING).limit(limit)
            matches = list(cursor)
            
            # If no exact match, try partial match
            if not matches:
                partial_query = {"object_name": {"$regex": object_name.strip(), "$options": "i"}}
                cursor = self.collection.find(partial_query, PUBLIC_PROJECTION).sort("timestamp", DESCENDING).limit(limit)
                matches = list(cursor)

            for rec in matches:
                if "timestamp" in rec and hasattr(rec["timestamp"], "isoformat"):
                    rec["timestamp"] = rec["timestamp"].isoformat()
            return matches
        except Exception as e:
            logger.error(f"Error querying object history for '{object_name}': {e}")
            return []

    # ------------------------------------------------------------------
    # Visual RAG / Atlas Vector Search
    # ------------------------------------------------------------------

    def vector_search(
        self,
        query_vector: List[float],
        embedding_model: str,
        limit: int = 5,
        index_name: Optional[str] = None,
        num_candidates: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Run an Atlas `$vectorSearch` restricted to vectors produced by the same embedding model.

        Raises:
            pymongo.errors.OperationFailure: when the deployment does not support
            `$vectorSearch` (e.g. a non-Atlas MongoDB). Callers are expected to fall back.
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": index_name or settings.VECTOR_INDEX_NAME,
                    "path": "image_embedding",
                    "queryVector": query_vector,
                    "numCandidates": num_candidates or max(limit * 20, 100),
                    "limit": limit,
                    "filter": {"embedding_model": embedding_model}
                }
            },
            {"$addFields": {"similarity_score": {"$meta": "vectorSearchScore"}}},
            {"$project": {**PUBLIC_PROJECTION, "tts_audio_base64": 0}}
        ]
        return _normalize_timestamps(list(self.collection.aggregate(pipeline)))

    def find_with_embeddings(self, embedding_model: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch recent documents that carry an embedding from the given model (brute-force fallback source)."""
        cursor = self.collection.find(
            {"embedding_model": embedding_model, "image_embedding": {"$type": "array"}},
            {"_id": 0, "tts_audio_base64": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return _normalize_timestamps(list(cursor))

    def find_missing_embeddings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch documents (including '_id') that do not yet have an embedding, for backfilling."""
        cursor = self.collection.find(
            {"$or": [{"image_embedding": None}, {"image_embedding": {"$exists": False}}]},
            {"tts_audio_base64": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(cursor)

    def set_embedding(self, doc_id: Any, vector: List[float], embedding_model: str) -> bool:
        """Attach an embedding vector (and its model tag) to an existing document."""
        result = self.collection.update_one(
            {"_id": doc_id},
            {"$set": {"image_embedding": vector, "embedding_model": embedding_model}}
        )
        return result.modified_count > 0

    def ensure_vector_index(self, dimensions: int, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Create the Atlas Vector Search index on 'image_embedding' if it does not exist yet."""
        from pymongo.operations import SearchIndexModel

        name = index_name or settings.VECTOR_INDEX_NAME
        definition = {
            "fields": [
                {"type": "vector", "path": "image_embedding", "numDimensions": dimensions, "similarity": "cosine"},
                {"type": "filter", "path": "embedding_model"}
            ]
        }
        existing = [idx.get("name") for idx in self.collection.list_search_indexes()]
        if name in existing:
            return {"status": "exists", "index_name": name, "definition": definition}

        self.collection.create_search_index(
            SearchIndexModel(definition=definition, name=name, type="vectorSearch")
        )
        logger.info(f"Created Atlas Vector Search index '{name}' ({dimensions} dims, cosine)")
        return {"status": "created", "index_name": name, "definition": definition}

# Singleton repository instance
detection_repo = DetectionRepository()
