import io
from app.core.config import get_settings

# Whisper language codes Whisper's own multilingual model actually ships
# (ISO 639-1, mostly). Dari (prs) has no distinct Whisper training
# language — Dari and Farsi are close enough that "fa" is the nearest
# usable hint, but this is a real accuracy caveat, not a bug: transcripts
# for Dari speech may lean toward Farsi spelling/vocabulary choices.
WHISPER_LANGUAGE_HINT = {
    "en": "en", "nl": "nl", "fr": "fr", "de": "de", "it": "it",
    "es": "es", "ru": "ru", "zh": "zh", "fa": "fa", "prs": "fa",
}

_model = None

def get_model():
    # Lazy singleton: loading the model (downloading + initializing
    # ctranslate2 weights) is expensive, so it happens once per process on
    # first real request rather than at every call or at import time
    # (which would slow down/break routes that never touch STT).
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        settings = get_settings()
        _model = WhisperModel(
            settings.whisper_model_size,
            device="cpu",
            compute_type=settings.whisper_compute_type,
        )
    return _model

def transcribe_audio(audio_bytes: bytes, language_code: str | None) -> str:
    """Transcribe raw audio bytes (any container ffmpeg/PyAV can decode —
    webm/opus from MediaRecorder is the expected input) to text. The caller
    is responsible for discarding audio_bytes immediately after this
    returns — this function never writes the audio to disk or logs it."""
    model = get_model()
    hint = WHISPER_LANGUAGE_HINT.get(language_code) if language_code else None
    segments, _info = model.transcribe(
        io.BytesIO(audio_bytes),
        language=hint,
        beam_size=1,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
