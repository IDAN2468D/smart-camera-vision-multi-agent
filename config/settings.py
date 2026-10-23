import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

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

    # Camera & Vision Configuration
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
    TEMP_FRAME_PATH: Path = BASE_DIR / "temp_frame.jpg"

    # Flask REST API Configuration
    FLASK_HOST: str = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))

settings = Settings()
