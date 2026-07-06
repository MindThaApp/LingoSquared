import json
import httpx
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape
from google.cloud import texttospeech
from google.oauth2 import service_account
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import TTSUsage

# Google Cloud TTS has no Persian/Dari voices at all — confirmed against
# Google's own supported-voices list. Those two languages always fall
# back to Azure (fa only, see below) or the browser (prs, still no
# real-voice provider found anywhere).
GOOGLE_TTS_SUPPORTED_LANGUAGES={"en","nl","fr","de","it","es","ru","zh"}

GOOGLE_TTS_LANGUAGE_CODE={
    "en":"en-US","nl":"nl-NL","fr":"fr-FR","de":"de-DE",
    "it":"it-IT","es":"es-ES","ru":"ru-RU","zh":"cmn-CN",
}

# Azure Cognitive Services Speech covers the one real gap Google leaves:
# Farsi (fa). Confirmed real, licensed neural voices exist —
# fa-IR-DilaraNeural (female, used as the default here) and
# fa-IR-FaridNeural (male) — via Azure's own voice gallery. Dari (prs)
# has no Azure voice either, so prs is unaffected and still falls all
# the way through to the browser.
AZURE_TTS_SUPPORTED_LANGUAGES={"fa"}

AZURE_TTS_LOCALE={"fa":"fa-IR"}
AZURE_TTS_VOICE_NAME={"fa":"fa-IR-DilaraNeural"}

# The authoritative "does /tts have a real cloud voice for this language"
# set — used by the route's supported-language gate and by the Endless
# Practice engine's listen_select gate. Keep this the union of every
# provider below rather than hardcoding a provider-specific set at each
# call site.
TTS_SUPPORTED_LANGUAGES=GOOGLE_TTS_SUPPORTED_LANGUAGES|AZURE_TTS_SUPPORTED_LANGUAGES

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

def synthesize_google(text_value:str,language_code:str) -> bytes:
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

def _azure_access_token(settings) -> str:
    # The Speech REST synthesize endpoint requires a short-lived bearer
    # token (not the raw subscription key) — exchanged fresh per request
    # here rather than cached, since TTS calls are already rate-limited by
    # the monthly character budget and a 10-minute token cache isn't worth
    # the added state for this call volume.
    response=httpx.post(
        f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
        headers={"Ocp-Apim-Subscription-Key":settings.azure_speech_key},
        timeout=10,
    )
    response.raise_for_status()
    return response.text

def synthesize_azure(text_value:str,language_code:str) -> bytes:
    settings=get_settings()
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise RuntimeError("Azure Speech credentials are not configured")
    token=_azure_access_token(settings)
    locale=AZURE_TTS_LOCALE[language_code]
    voice=AZURE_TTS_VOICE_NAME[language_code]
    ssml=(
        f"<speak version='1.0' xml:lang='{locale}'>"
        f"<voice xml:lang='{locale}' name='{voice}'>{xml_escape(text_value)}</voice>"
        f"</speak>"
    )
    response=httpx.post(
        f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1",
        content=ssml.encode("utf-8"),
        headers={
            "Authorization":f"Bearer {token}",
            "Content-Type":"application/ssml+xml",
            "X-Microsoft-OutputFormat":"audio-24khz-48kbitrate-mono-mp3",
            "User-Agent":"LingoSquared",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.content

def synthesize(text_value:str,language_code:str) -> bytes:
    # Routing: Azure covers the one real gap Google leaves (fa); every
    # other already-covered language keeps using Google unchanged. Add
    # new providers here, not by replacing this dispatch.
    if language_code in AZURE_TTS_SUPPORTED_LANGUAGES:
        return synthesize_azure(text_value,language_code)
    return synthesize_google(text_value,language_code)
