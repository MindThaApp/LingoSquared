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
GOOGLE_TTS_SUPPORTED_LANGUAGES={"en","nl","fr","de","it","es","ru","zh","pl","ro","hi"}

GOOGLE_TTS_LANGUAGE_CODE={
    "en":"en-US","nl":"nl-NL","fr":"fr-FR","de":"de-DE",
    "it":"it-IT","es":"es-ES","ru":"ru-RU","zh":"cmn-CN",
    "pl":"pl-PL","ro":"ro-RO","hi":"hi-IN",
}

# Without an explicit voice `name`, Google Cloud TTS resolves language_code
# + ssml_gender to WHATEVER voice it defaults to for that combination —
# frequently an old, low-quality "Standard" voice, not the much more
# natural Neural2/WaveNet tiers Google also offers for the same language.
# Confirmed live 2026-07-09 via a real texttospeech.list_voices() call
# against this project's actual credentials (not guessed from training
# data, which can be stale/wrong about what's currently offered) — every
# non-TODO name below is real and currently available. Neural2 doesn't
# cover nl/ru/zh/pl/ro yet, so those five fall back to WaveNet (still
# far more natural than Standard).
GOOGLE_TTS_VOICE_NAME={
    "en":"en-US-Neural2-C","nl":"nl-NL-Wavenet-F","fr":"fr-FR-Neural2-F",
    "de":"de-DE-Neural2-G","it":"it-IT-Neural2-A","es":"es-ES-Neural2-A",
    "ru":"ru-RU-Wavenet-C","zh":"cmn-CN-Wavenet-A",
    "pl":"pl-PL-Wavenet-F","ro":"ro-RO-Wavenet-B",
    # TODO: Placeholder only -- not yet verified against this project's
    # real texttospeech.list_voices() output the way the entries above were.
    "hi":"hi-IN-Neural2-A",
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
# set — used by the route's supported-language gate. NOTE: this is
# static language-membership only, NOT proof the responsible provider
# actually has credentials configured right now — see
# `tts_actually_configured()` below, which the Endless Practice engine's
# listen_select gate uses instead. A 2026-07-07 Fable audit flagged a
# real latent trap: `fa` was added to this set once Azure was wired up,
# but `azure_speech_key` defaults to empty, so gating generation on
# language-membership alone would let listen_select items generate for
# fa with no real voice configured yet — the exact unanswerable-audio
# class already hit twice this project (Vite HMR aside), just via a
# different mechanism each time.
TTS_SUPPORTED_LANGUAGES=GOOGLE_TTS_SUPPORTED_LANGUAGES|AZURE_TTS_SUPPORTED_LANGUAGES

def tts_actually_configured(language_code:str) -> bool:
    """Whether this language's real provider has real credentials right
    now, not just whether the language is nominally in a supported set.
    Use this (not `TTS_SUPPORTED_LANGUAGES`) anywhere generating content
    depends on TTS actually producing audio, e.g. the Endless Practice
    listen_select gate — a language can be in `TTS_SUPPORTED_LANGUAGES`
    (added the day a provider integration merges) while the deploy target
    still has an empty credential, same as Google's already-established
    "may produce no sound" browser-fallback risk, just earlier in the
    pipeline."""
    settings=get_settings()
    if language_code in GOOGLE_TTS_SUPPORTED_LANGUAGES:
        return bool(settings.google_cloud_tts_credentials_json)
    if language_code in AZURE_TTS_SUPPORTED_LANGUAGES:
        return bool(settings.azure_speech_key and settings.azure_speech_region)
    return False

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

def synthesize_google(text_value:str,language_code:str,speaking_rate:float=1.0) -> bytes:
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
            name=GOOGLE_TTS_VOICE_NAME[language_code],
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            # 1.0 = native speed; [0.25, 2.0] is the library's own supported
            # range (see `google.cloud.texttospeech_v1.types.AudioConfig`'s
            # docstring) — the /tts route validates the same bound before
            # it ever reaches here, via TTSIn.speaking_rate.
            speaking_rate=speaking_rate,
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

def synthesize_azure(text_value:str,language_code:str,speaking_rate:float=1.0) -> bytes:
    settings=get_settings()
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise RuntimeError("Azure Speech credentials are not configured")
    token=_azure_access_token(settings)
    locale=AZURE_TTS_LOCALE[language_code]
    voice=AZURE_TTS_VOICE_NAME[language_code]
    # The Speech REST API has no top-level rate field the way Google's
    # AudioConfig does — SSML's <prosody rate="..."> is the equivalent
    # lever. Percentage form (e.g. 0.9 -> "-10%") is well-documented and
    # avoids the ambiguity of the bare-multiplier form. Always wrapped
    # (even at the 1.0 default -> "+0%") to keep this one code path.
    rate_percent=f"{(speaking_rate-1.0)*100:+.0f}%"
    ssml=(
        f"<speak version='1.0' xml:lang='{locale}'>"
        f"<voice xml:lang='{locale}' name='{voice}'>"
        f"<prosody rate='{rate_percent}'>{xml_escape(text_value)}</prosody>"
        f"</voice>"
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

def synthesize(text_value:str,language_code:str,speaking_rate:float=1.0) -> bytes:
    # Routing: Azure covers the one real gap Google leaves (fa); every
    # other already-covered language keeps using Google unchanged. Add
    # new providers here, not by replacing this dispatch.
    if language_code in AZURE_TTS_SUPPORTED_LANGUAGES:
        return synthesize_azure(text_value,language_code,speaking_rate)
    return synthesize_google(text_value,language_code,speaking_rate)
