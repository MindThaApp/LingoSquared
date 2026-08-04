from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Auvel API"
    database_url: str = "postgresql+psycopg://lingosquared:change-me@db:5432/lingosquared"
    jwt_secret: str = "development-only-secret"
    access_token_expire_seconds: int = 1800
    refresh_token_expire_seconds: int = 60 * 24 * 60 * 60
    admin_emails: str = "admin@example.com"
    cors_origins: str = "http://localhost:5173"
    # Raw service-account JSON content (not a file path) — set as a single
    # env var so credentials don't require a mounted file in every deploy
    # environment.
    google_cloud_tts_credentials_json: str = ""
    # Google's free tier for Standard voices is 4M characters/month.
    tts_monthly_char_budget: int = 4000000
    # Azure Cognitive Services Speech — covers Farsi (fa), the one real
    # gap Google's TTS leaves. Subscription key + region, same
    # unset-by-default/graceful-degradation convention as the Google
    # credential above: empty until a real key is provisioned, and
    # synthesize_azure() raises (caught by the /tts route, which falls
    # back to browser speechSynthesis) rather than crashing when unset.
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    # Self-hosted Whisper fallback STT (only hit when the client reports
    # client-side WASM transcription isn't available). "tiny"/"base" keep
    # CPU latency reasonable on a modest self-hosted box; int8 quantization
    # trades a little accuracy for speed/memory on CPU-only inference.
    whisper_model_size: str = "base"
    whisper_compute_type: str = "int8"
    # Rate limit ceilings (see app/core/rate_limit.py). Defaults match the
    # values that shipped hardcoded on 2026-07-06 -- pulled into Settings so
    # an isolated test/CI environment (which legitimately needs to register
    # far more than 5 accounts/hour from one IP -- the e2e suite registers a
    # fresh user per spec) can raise them via env vars without touching the
    # production defaults. Window durations stay hardcoded in router.py;
    # only the request-count ceilings are configurable, since that's the
    # dimension a test environment actually needs to move.
    login_rate_limit_max: int = 10
    register_rate_limit_max: int = 5
    # POST /auth/refresh shipped 2026-07-10 with no rate limit at all -- an
    # unauthenticated endpoint whose token lookup bcrypt-verifies the
    # presented value against every stored refresh-token hash, so hammering
    # it (replaying a stolen-but-not-yet-rotated token, or probing for valid
    # tokens) is both a guessing surface and a CPU sink. Deliberately more
    # generous than login's 10/min: legitimate clients refresh automatically
    # on access-token expiry (plus tab wakeups/retries) and several devices
    # can share one NAT'd IP. The same limiter also covers /auth/logout,
    # which takes the same unauthenticated refresh-token body and pays the
    # same full-table bcrypt scan.
    refresh_rate_limit_max: int = 30
    answer_rate_limit_max: int = 120
    # Phase H2 (2026-07-07 integrity audit): the three limiters above left
    # /tts, /stt/transcribe, and the three generation endpoints (reviews/
    # session, practice/batch, units/checkpoint) completely unrated -- see
    # docs/SONNET_BUILD_PROMPT_LAUNCH.md Phase H2 for the full finding.
    tts_rate_limit_max: int = 30
    # Per-account daily character cap for /tts, separate from the existing
    # shared monthly budget in TTSUsage -- that budget is account-agnostic,
    # so one account could exhaust it alone. Two orders of magnitude above
    # any real day of use.
    tts_daily_char_cap: int = 100000
    stt_rate_limit_max: int = 10
    # Shared across /reviews/session, /practice/{course_id}/batch, and
    # /units/{unit_id}/checkpoint -- all three do the same heavy batch
    # generation work.
    generation_rate_limit_max: int = 20
    # Phase H4: /exercises/{id}/report and /practice/items/{id}/report
    # never had any rate limit at all.
    report_rate_limit_max: int = 20
    # Web push (Phase E4) — VAPID keypair, same unset-by-default/graceful-
    # degradation convention as the TTS credentials above: empty until
    # provisioned (generate with `vapid --gen` from the py-vapid package,
    # a pywebpush dependency), and /push/subscribe + the send path both
    # fail closed (503) rather than crash when unset.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"
    google_oauth_client_ids: str = ""
    apple_audience_ids: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admin_email_set(self): return {x.strip().lower() for x in self.admin_emails.split(",") if x.strip()}
    @property
    def cors_origin_list(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
    @property
    def google_oauth_client_id_set(self): return {x.strip() for x in self.google_oauth_client_ids.split(",") if x.strip()}
    @property
    def apple_audience_id_set(self): return {x.strip() for x in self.apple_audience_ids.split(",") if x.strip()}

@lru_cache
def get_settings(): return Settings()
