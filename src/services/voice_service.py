"""Voice transcription service using local Whisper inference."""

import asyncio
import logging
import re
from typing import Optional

try:
    import whisper
except ImportError:  # pragma: no cover
    whisper = None

# Custom exception alignment for service interface safety
class VoiceServiceError(Exception):
    """Custom exception for voice service failures."""
    pass

logger = logging.getLogger(__name__)


class VoiceService:
    """Transcribes audio to text using local Whisper model with conversational cleaning."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if whisper is None:
            raise VoiceServiceError("Whisper package is not installed in the current environment.")
        if self._model is None:
            logger.info("Loading local Whisper model ('base')...")
            self._model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully.")
        return self._model

    def _clean_transcript(self, text: str) -> str:
        """
        Cleans up conversational artifacts, hallucinated repetitive phrases from silence,
        and standardizes key automation phrases for Phase 1 execution.
        """
        # Remove aggressive punctuation and trailing spaces
        text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?]', '', text)
        text = text.strip()

        # Handle typical Whisper silence hallucination loops
        hallucinations = ["you", "thank you", "thanks for watching", "bye"]
        if text.lower() in hallucinations:
            return ""

        return text

    def _transcribe_sync(self, audio_path: str) -> str:
        model = self._get_model()
        # Enforce English language constraint to boost speed and precision for Phase 1 commands
        result = model.transcribe(audio_path, fp16=False, language="en")
        raw_text = (result.get("text") or "").strip()
        
        return self._clean_transcript(raw_text)

    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Asynchronously processes an audio clip path by offloading synchronous processing 
        to a threadpool pool worker.
        """
        try:
            cleaned_text = await asyncio.to_thread(self._transcribe_sync, audio_path)
            logger.info(f"Successfully transcribed audio. Result: '{cleaned_text}'")
            return cleaned_text
        except Exception as exc:
            logger.error(f"Voice transcription process failed: {exc}")
            raise VoiceServiceError(str(exc))


# Global Singleton pattern initialization
voice_service = None


def get_voice_service() -> VoiceService:
    """Returns the globally shared VoiceService runtime module instance."""
    global voice_service
    if voice_service is None:
        voice_service = VoiceService()
    return voice_service