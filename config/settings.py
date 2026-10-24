import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Disable external Agno cloud telemetry to eliminate blocking remote calls on every agent run
os.environ["AGNO_TELEMETRY"] = "false"
os.environ["AGNO_TELEMETRY_ENABLED"] = "false"

class Settings:
    """Central configuration settings for the vision recognition system."""
    
    BASE_DIR: Path = BASE_DIR
    
    # MongoDB Atlas Configuration
    MONGO_URI: str = os.getenv(
        "MONGO_URI",
        "mongodb+srv://idankzm:idankzm2468@cluster0.purdk.mongodb.net/?retryWrites=true&w=majority"
    )
    DB_NAME: str = os.getenv("DB_NAME", "vision_agents_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "detections")

    # Gemini & AI Model Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL_ID: str = os.getenv("MODEL_ID", "gemini-3.5-flash-lite")

    # Embedding & Visual RAG (Atlas Vector Search) Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "768"))
    VECTOR_INDEX_NAME: str = os.getenv("VECTOR_INDEX_NAME", "vector_index")
    # Minimum normalized cosine score (0..1, Atlas scale) for a past detection to count as "similar"
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))

    # Camera & Vision Configuration
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
    TEMP_FRAME_PATH: Path = BASE_DIR / "temp_frame.jpg"

    # Flask REST API Configuration
    FLASK_HOST: str = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))

settings = Settings()
