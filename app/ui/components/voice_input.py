"""Reusable voice input widget backed by Groq Whisper transcription.

Usage::

    from app.ui.components.voice_input import render_voice_input

    transcript = render_voice_input(key="my_page")
    if transcript:
        st.write(f"You said: {transcript}")

The widget caches transcriptions by audio fingerprint so unrelated page
reruns do not trigger redundant API calls.
"""

from __future__ import annotations

import hashlib

import streamlit as st

from app.ai.whisper import SUPPORTED_LANGUAGES, WhisperService


def render_voice_input(
    key: str = "voice",
    label: str = "🎙 Record your voice command",
    help_text: str | None = None,
) -> str | None:
    """Render a language selector + audio recorder and return the transcript.

    Args:
        key: Unique prefix for all session-state and widget keys on this page.
        label: Text shown above the audio recorder widget.
        help_text: Optional caption shown below the language selector.

    Returns:
        The latest transcription string, or ``None`` if nothing has been
        recorded yet or transcription failed.
    """
    lang_col, _ = st.columns([1, 3])
    with lang_col:
        language_label = st.selectbox(
            "Language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            key=f"{key}_lang",
            label_visibility="collapsed",
        )
    if help_text:
        st.caption(help_text)

    language_code = SUPPORTED_LANGUAGES[language_label]
    audio = st.audio_input(label, key=f"{key}_audio")

    if audio is None:
        return st.session_state.get(f"{key}_transcript")

    audio_bytes = audio.getvalue()
    if not audio_bytes:
        return st.session_state.get(f"{key}_transcript")

    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    hash_key = f"{key}_hash"
    transcript_key = f"{key}_transcript"

    if st.session_state.get(hash_key) != audio_hash:
        st.session_state[hash_key] = audio_hash
        st.session_state[f"{key}_processing"] = True
        with st.spinner("Transcribing…"):
            try:
                text = WhisperService().transcribe(audio_bytes, language_code=language_code)
                st.session_state[transcript_key] = text
            except ValueError as exc:
                st.error(str(exc))
                st.session_state[transcript_key] = None
                st.session_state[f"{key}_processing"] = False
                return None
            except Exception as exc:
                st.error(f"Transcription failed: {exc}")
                st.session_state[transcript_key] = None
                st.session_state[f"{key}_processing"] = False
                return None
        st.session_state[f"{key}_processing"] = False

    transcript = st.session_state.get(transcript_key)
    if transcript:
        st.markdown(
            f"""
            <div class="voice-transcript" style="animation: pageFadeIn .3s ease-out;">
              <span class="voice-icon">🎙</span> {transcript}
            </div>
            """,
            unsafe_allow_html=True,
        )
    return transcript

