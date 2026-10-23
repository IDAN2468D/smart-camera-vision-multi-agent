from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field

class VisionAnalysisResult(BaseModel):
    """Structured output schema for VisionPerceptionAgent."""
    object_name: str = Field(..., description="Name of the main detected item, person, face, hand, or object in English")
    category: str = Field(..., description="Category (e.g., Human/Person, Face, Anatomy/Hands, Electronics, Drinkware, Stationery, Tool)")
    detected_entities: List[str] = Field(
        default_factory=list,
        description="Comprehensive list of all items, anatomy, and objects detected in the frame (e.g., ['Human Face', 'Right Hand', 'Smartphone', 'Eyeglasses'])"
    )
    face_detected: bool = Field(default=False, description="True if a human face is clearly visible in the frame")
    hands_detected: bool = Field(default=False, description="True if human hands, palms, or gestures are visible in the frame")
    detected_text: Optional[str] = Field(default=None, description="Any readable text found on clothes, screens, labels, or objects via OCR")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the visual recognition between 0.0 and 1.0")
    visual_description: str = Field(..., description="Detailed visual description of the person, face, hands, gestures, held objects, colors, and setting")

class ProductPriceInfo(BaseModel):
    """Commerce and price estimation details for detected products."""
    model_name: str = Field(..., description="Specific product or model name")
    estimated_price_ils: Optional[str] = Field(default=None, description="Estimated market price range in ILS (₪)")
    specs_summary: Optional[str] = Field(default=None, description="Short technical specifications summary in Hebrew")
    source_url: Optional[str] = Field(default=None, description="Source reference link")

class DetectionRecord(VisionAnalysisResult):
    """Complete detection record including multi-agent enrichment, media, and persistence timestamp."""
    enrichment_summary: str = Field(..., description="Contextual insights and historical correlation from MongoDB provided by KnowledgeEnrichmentAgent in Hebrew")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the detection occurred"
    )
    trigger_source: str = Field(default="manual_space", description="Trigger mechanism: manual_space | auto_timer | gesture_thumbs_up | web_hud")
    gesture_detected: Optional[str] = Field(default=None, description="Recognized gesture: thumbs_up | open_palm | pointing | none")
    recognized_person_name: Optional[str] = Field(default=None, description="Recognized user name (e.g. 'עידן')")
    product_info: Optional[ProductPriceInfo] = Field(default=None, description="Commercial price and product specifications")
    thumbnail_base64: Optional[str] = Field(default=None, description="Compressed WebP thumbnail for visual timeline")
    tts_audio_base64: Optional[str] = Field(default=None, description="Base64 encoded MP3 speech audio of the Hebrew insight")
    image_embedding: Optional[List[float]] = Field(default=None, description="Visual embedding vector for Atlas Vector Search")
