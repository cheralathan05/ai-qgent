"""Voice transcription service using local Whisper inference."""

import asyncio
import logging
from typing import Optional

try:
    import whisper
except ImportError:  # pragma: no cover
    whisper = None

from services.ollama_service import OllamaServiceError

logger = logging.getLogger(__name__)


class VoiceService:
    """Transcribes audio to text using local Whisper model."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if whisper is None:
            raise OllamaServiceError("whisper is not installed")
        if self._model is None:
            self._model = whisper.load_model("base")
        return self._model

    def _transcribe_sync(self, audio_path: str) -> str:
        model = self._get_model()
        result = model.transcribe(audio_path, fp16=False)
        return (result.get("text") or "").strip()

    async def transcribe_audio(self, audio_path: str) -> str:
        try:
            return await asyncio.to_thread(self._transcribe_sync, audio_path)
        except Exception as exc:
            logger.error(f"Voice transcription failed: {exc}")
            raise OllamaServiceError(str(exc))


voice_service = None


def get_voice_service() -> VoiceService:
    global voice_service
    if voice_service is None:
        voice_service = VoiceService()
    return voice_service
