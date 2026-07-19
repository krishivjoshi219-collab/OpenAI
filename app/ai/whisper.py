"""Groq Whisper speech-to-text transcription service.

Uses Groq's audio transcription endpoint (OpenAI-compatible) to convert
recorded audio to text in English or Hindi.  Requires ``GROQ_API_KEY``
in the environment — the same key used for the Groq LLM provider.
"""

from __future__ import annotations

import io

from openai import OpenAI

from config.settings import get_settings

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_WHISPER_MODEL = "whisper-large-v3-turbo"

# Human-readable label → ISO 639-1 language code
SUPPORTED_LANGUAGES: dict[str, str] = {
    "English 🇬🇧": "en",
    "Hindi 🇮🇳": "hi",
}


class WhisperService:
    """Transcribe audio bytes using Groq's Whisper endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is required for voice transcription. "
                "Add it to your Replit Secrets and restart the app."
            )
        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=_GROQ_BASE_URL,
        )

    def transcribe(self, audio_bytes: bytes, language_code: str = "en") -> str:
        """Convert raw audio bytes to a transcribed text string.

        Args:
            audio_bytes: Raw audio in WAV, MP3, M4A, OGG, or FLAC format.
            language_code: ISO 639-1 code — ``'en'`` or ``'hi'``.

        Returns:
            Stripped transcription string.

        Raises:
            ValueError: If the API key is missing or the audio is empty.
        """
        if not audio_bytes:
            raise ValueError("No audio data provided.")

        audio_file = ("recording.wav", io.BytesIO(audio_bytes), "audio/wav")
        response = self._client.audio.transcriptions.create(
            file=audio_file,
            model=_WHISPER_MODEL,
            language=language_code,
            response_format="text",
        )
        # Groq returns a plain string when response_format="text"
        return str(response).strip()
