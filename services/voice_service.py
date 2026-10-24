import io
import re
import os
import base64
import asyncio
import logging
from typing import Optional
import edge_tts

logger = logging.getLogger(__name__)

class VoiceService:
    """Hebrew Voice Agent (TTS) service using edge-tts for natural neural speech synthesis.
    
    Supports both decoupled microservice HTTP calls and in-process local execution.
    """

    DEFAULT_VOICE = "he-IL-AvriNeural"  # Natural Hebrew male voice (Alternative: "he-IL-HilaNeural")

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice
        self._audio_cache: dict = {}

    @staticmethod
    def _clean_text_for_speech(text: str) -> str:
        """Strip markdown syntax, URLs, bullet points and symbols for pleasant pronunciation."""
        if not text:
            return ""
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'[*_~`#>]', ' ', text)
        text = re.sub(r'^\s*[-+*]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*\n+\s*', '. ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    async def _synthesize_async(self, text: str, voice: str) -> bytes:
        """Asynchronously stream audio chunks from edge-tts into memory buffer."""
        communicate = edge_tts.Communicate(text, voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

    def generate_speech(self, text: str, voice: Optional[str] = None) -> Optional[str]:
        """Synthesize Hebrew text into Base64 encoded MP3 audio.
        
        Args:
            text: Text to speak (Hebrew summary or description).
            voice: Voice name override (default: he-IL-AvriNeural).
            
        Returns:
            Data URI string (data:audio/mp3;base64,...) or None if failed.
        """
        clean_text = self._clean_text_for_speech(text)
        if not clean_text:
            return None

        words = clean_text.split()
        # Allow reading full insight without cutting off mid-sentence.
        # Only cap extremely long inputs (>120 words) at a natural sentence boundary.
        if len(words) > 120:
            truncated = " ".join(words[:120])
            last_period = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))
            if last_period > 40:
                clean_text = truncated[:last_period + 1].strip()
            else:
                clean_text = truncated.strip() + "."

        target_voice = voice or self.voice
        cache_key = f"{target_voice}_{clean_text}"
        if cache_key in self._audio_cache:
            logger.info("[VoiceService] Returning cached audio (0ms)")
            return self._audio_cache[cache_key]

        # 1. Attempt calling dedicated Voice Microservice if configured
        voice_service_url = os.environ.get("VOICE_SERVICE_URL")
        if voice_service_url:
            try:
                import requests
                res = requests.post(
                    f"{voice_service_url}/synthesize",
                    json={"text": clean_text, "voice": target_voice},
                    timeout=25
                )
                if res.status_code == 200:
                    data = res.json()
                    b64 = data.get("audio_base64")
                    if b64:
                        logger.info(f"[Microservice] Successfully synthesized audio via {voice_service_url}")
                        self._audio_cache[cache_key] = b64
                        return b64
            except Exception as net_err:
                logger.warning(f"Voice microservice call failed ({net_err}). Falling back to local synthesis.")

        # 2. Local in-process synthesis fallback
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                audio_bytes = executor.submit(
                    lambda: asyncio.run(self._synthesize_async(clean_text, target_voice))
                ).result(timeout=25)

            if not audio_bytes:
                logger.warning("edge-tts returned empty audio buffer")
                return None

            encoded = base64.b64encode(audio_bytes).decode("utf-8")
            data_uri = f"data:audio/mp3;base64,{encoded}"
            self._audio_cache[cache_key] = data_uri
            logger.info(f"Synthesized full Hebrew speech ({len(audio_bytes)} bytes) for: '{clean_text[:45]}...'")
            return data_uri

        except Exception as e:
            logger.error(f"Failed to synthesize Hebrew speech with edge-tts: {e}")
            return None

# Singleton service instance
voice_service = VoiceService()
