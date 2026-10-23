import io
import base64
import logging
from typing import Optional, Union
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

class ThumbnailService:
    """Service for compressing and converting camera snapshots into optimized WebP thumbnails."""

    def __init__(self, default_size=(320, 180), default_quality=80):
        self.default_size = default_size
        self.default_quality = default_quality

    def create_webp_thumbnail(
        self,
        image_source: Union[str, Path, bytes, io.BytesIO],
        max_size: Optional[tuple] = None,
        quality: Optional[int] = None
    ) -> Optional[str]:
        """Convert an image from path or bytes into a lightweight Base64 WebP thumbnail.
        
        Args:
            image_source: Path to image file, raw bytes, or BytesIO buffer.
            max_size: Maximum (width, height) bounding box (default: (320, 180)).
            quality: WebP compression quality 1-100 (default: 80).
            
        Returns:
            Data URI string (data:image/webp;base64,...) or None if failed.
        """
        size = max_size or self.default_size
        q = quality or self.default_quality

        try:
            if isinstance(image_source, (str, Path)):
                img = Image.open(str(image_source))
            elif isinstance(image_source, bytes):
                img = Image.open(io.BytesIO(image_source))
            elif isinstance(image_source, io.BytesIO):
                img = Image.open(image_source)
            else:
                logger.warning(f"Unsupported image source type: {type(image_source)}")
                return None

            # Convert RGBA/P to RGB for clean WebP compression
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # High quality thumbnail resize maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=q, method=6)
            webp_bytes = buffer.getvalue()

            encoded = base64.b64encode(webp_bytes).decode("utf-8")
            data_uri = f"data:image/webp;base64,{encoded}"
            
            logger.debug(f"Generated WebP thumbnail ({len(webp_bytes)} bytes)")
            return data_uri

        except Exception as e:
            logger.error(f"Failed to generate WebP thumbnail: {e}")
            return None

# Singleton service instance
thumbnail_service = ThumbnailService()
