import logging
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from config.settings import settings
from models.detection_schema import DetectionRecord

logger = logging.getLogger(__name__)

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
            cursor = self.collection.find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
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
            cursor = self.collection.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
            matches = list(cursor)
            
            # If no exact match, try partial match
            if not matches:
                partial_query = {"object_name": {"$regex": object_name.strip(), "$options": "i"}}
                cursor = self.collection.find(partial_query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
                matches = list(cursor)

            for rec in matches:
                if "timestamp" in rec and hasattr(rec["timestamp"], "isoformat"):
                    rec["timestamp"] = rec["timestamp"].isoformat()
            return matches
        except Exception as e:
            logger.error(f"Error querying object history for '{object_name}': {e}")
            return []

# Singleton repository instance
detection_repo = DetectionRepository()
