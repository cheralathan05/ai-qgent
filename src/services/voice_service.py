"""Voice transcription service using Whisper local model via Ollama."""

import asyncio
import logging
from typing import Dict, Any
from services.ollama_service import get_ollama_service, OllamaServiceError

logger = logging.getLogger(__name__)


class VoiceService:
    """Transcribes audio to text using local Whisper model."""

    PROMPT_TEMPLATE = "Transcribe the following audio into text. Return plain text only."

    def __init__(self):
        self.ollama_service = get_ollama_service()

    async def transcribe_audio(self, audio_path: str) -> str:
        try:
            prompt = f"{self.PROMPT_TEMPLATE}\nAudio file: {audio_path}\n"
            result = await self.ollama_service.generate(prompt, max_tokens=256)
            if "choices" in result and result["choices"]:
                return result["choices"][0].get("text", "").strip()
            return ""
        except Exception as exc:
            logger.error(f"Voice transcription failed: {exc}")
            raise OllamaServiceError(str(exc))


voice_service = None


def get_voice_service() -> VoiceService:
    global voice_service
    if voice_service is None:
        voice_service = VoiceService()
    return voice_service
