"""Groq Whisper speech-to-text transcription service.

Uses Groq's audio transcription endpoint (OpenAI-compatible) to convert
recorded audio to text in English or Hindi.  Requires ``GROQ_API_KEY``
in the environment — the same key used for the Groq LLM provider.

On Streamlit Community Cloud the key can also be supplied via the BYOK
sidebar (stored in ``st.session_state["byok_groq_api_key"]``), which
takes precedence over the environment secret so users can try the voice
feature with their own key without a redeploy.
"""

from __future__ import annotations

import io

from config.settings import get_settings
from openai import OpenAI

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_WHISPER_MODEL = "whisper-large-v3-turbo"

# Human-readable label → ISO 639-1 language code
SUPPORTED_LANGUAGES: dict[str, str] = {
    "English 🇬🇧": "en",
    "Hindi 🇮🇳": "hi",
}


def _get_groq_api_key() -> str | None:
    """Return the Groq API key, preferring the BYOK sidebar value when set."""
    try:
        import streamlit as st  # noqa: PLC0415

        byok = st.session_state.get("byok_groq_api_key")
        if byok:
            return byok
    except Exception:  # noqa: BLE001
        pass
    return get_settings().groq_api_key


class WhisperService:
    """Transcribe audio bytes using Groq's Whisper endpoint."""

    def __init__(self) -> None:
        api_key = _get_groq_api_key()
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is required for voice transcription. "
                "Add it to your Replit Secrets or paste it into the "
                "Bring Your Own Key section in the sidebar."
            )
        self._client = OpenAI(
            api_key=api_key,
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
