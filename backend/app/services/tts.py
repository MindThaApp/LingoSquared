import json
from datetime import datetime, timezone
from google.cloud import texttospeech
from google.oauth2 import service_account
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import TTSUsage

# Google Cloud TTS has no Persian/Dari voices at all — confirmed against
# Google's own supported-voices list. Those two languages always fall
# back to the browser.
GOOGLE_TTS_SUPPORTED_LANGUAGES={"en","nl","fr","de","it","es","ru","zh"}

GOOGLE_TTS_LANGUAGE_CODE={
    "en":"en-US","nl":"nl-NL","fr":"fr-FR","de":"de-DE",
    "it":"it-IT","es":"es-ES","ru":"ru-RU","zh":"cmn-CN",
}

def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")

def reserve_characters(db:Session,characters:int) -> bool:
    settings=get_settings(); month=current_month()
    # PostgreSQL transaction advisory lock serializes creation/check/update of
    # the single monthly row, preventing concurrent requests overspending.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"),{"key":f"lingosquared-tts-{month}"})
    usage=db.scalar(select(TTSUsage).where(TTSUsage.month==month).with_for_update())
    if not usage:
        usage=TTSUsage(month=month,characters=0,updated_at=datetime.now(timezone.utc)); db.add(usage); db.flush()
    if usage.characters+characters > max(0,settings.tts_monthly_char_budget):
        db.rollback(); return False
    # Keep the reservation uncommitted, and therefore keep the advisory lock,
    # until the provider returns audio. The caller commits success or rolls
    # back failure, so failed generations never consume the monthly budget.
    usage.characters+=characters; usage.updated_at=datetime.now(timezone.utc); return True

def synthesize(text_value:str,language_code:str) -> bytes:
    settings=get_settings()
    if not settings.google_cloud_tts_credentials_json:
        raise RuntimeError("Google Cloud TTS credentials are not configured")
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(settings.google_cloud_tts_credentials_json)
    )
    client=texttospeech.TextToSpeechClient(credentials=credentials)
    response=client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text_value),
        voice=texttospeech.VoiceSelectionParams(
            language_code=GOOGLE_TTS_LANGUAGE_CODE[language_code],
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        ),
    )
    return response.audio_content
