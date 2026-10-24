from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SpatialBoundingBox(BaseModel):
    """Normalized 2D bounding box + 3D audio spatial coordinates."""
    label: str = Field(..., description="Entity or product label")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    x_min: float = Field(default=0.1, ge=0.0, le=1.0)
    y_min: float = Field(default=0.1, ge=0.0, le=1.0)
    x_max: float = Field(default=0.9, ge=0.0, le=1.0)
    y_max: float = Field(default=0.9, ge=0.0, le=1.0)
    pan_x: float = Field(default=0.0, ge=-1.0, le=1.0, description="Horizontal audio pan (-1 left to +1 right)")
    depth_z: float = Field(default=-1.0, description="Estimated relative depth for Web Audio PannerNode")

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
    spatial_bboxes: List[SpatialBoundingBox] = Field(
        default_factory=list,
        description="Normalized bounding boxes and 3D audio panning coordinates for detected entities"
    )

class ProductPriceInfo(BaseModel):
    """Commerce and price estimation details for detected products."""
    model_name: str = Field(..., description="Specific product or model name")
    estimated_price_ils: Optional[str] = Field(default=None, description="Estimated market price range in ILS (₪)")
    specs_summary: Optional[str] = Field(default=None, description="Short technical specifications summary in Hebrew")
    source_url: Optional[str] = Field(default=None, description="Source reference link")
    bbox: Optional[SpatialBoundingBox] = Field(default=None, description="Bounding box location in frame for AR Hotspot")
    store_name: Optional[str] = Field(default=None, description="Retail portal or store name (e.g. Zap, KSP, Ivory)")
    price_screenshot_base64: Optional[str] = Field(default=None, description="Live Playwright screenshot of retail price tag")

class SceneDeltaReport(BaseModel):
    """Temporal comparison against previous scan in the same zone."""
    added_entities: List[str] = Field(default_factory=list, description="Entities newly detected in the scene")
    removed_entities: List[str] = Field(default_factory=list, description="Entities that disappeared from the scene")
    dwell_time_seconds: Optional[int] = Field(default=None, description="Estimated presence duration")
    delta_summary_hebrew: Optional[str] = Field(default=None, description="Contextual delta explanation in Hebrew")

class CompareAnalysisResult(BaseModel):
    """Side-by-side comparison matrix between two items."""
    item_a_name: str
    item_b_name: str
    price_a_ils: Optional[str] = None
    price_b_ils: Optional[str] = None
    comparison_points: List[Dict[str, str]] = Field(default_factory=list, description="List of {'feature': X, 'item_a': Y, 'item_b': Z}")
    winner_recommendation_hebrew: str = Field(..., description="Synthesis and buying advice in Hebrew")

class AskVisionResponse(BaseModel):
    """Conversational question-answer response over live frame."""
    question_hebrew: str
    answer_hebrew: str
    tts_audio_base64: Optional[str] = None
    pan_x: float = Field(default=0.0, description="Spatial pan coordinate for 3D audio response")
    referenced_entities: List[str] = Field(default_factory=list)

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
    embedding_model: Optional[str] = Field(default=None, description="Embedding model that produced image_embedding (vectors are only comparable within the same model)")
    scene_delta: Optional[SceneDeltaReport] = Field(default=None, description="Scene diff against previous detection")
