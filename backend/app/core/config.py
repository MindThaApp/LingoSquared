from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Auvel API"
    app_env: str = "production"
    database_url: str = "postgresql+psycopg://lingosquared:change-me@db:5432/lingosquared"
    jwt_secret: str = "development-only-secret"
    access_token_expire_seconds: int = 1800
    refresh_token_expire_seconds: int = 60 * 24 * 60 * 60
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
    # unauthenticated endpoint whose token lookup is a fast indexed SHA-256
    # digest match. The limit still bounds replay and probing attempts, and
    # is more generous than login's 10/min because clients refresh on access
    # token expiry and several devices can share one NAT'd IP. The same
    # limiter covers /auth/logout.
    refresh_rate_limit_max: int = 30
    # How long after a rotation the immediately previous refresh token may
    # be presented again and receive the SAME successor back instead of
    # tripping reuse detection. Covers a response lost to a page reload and
    # two tabs refreshing at once. Outside this window (or once the
    # successor itself has been rotated or revoked) a rotated-out token is
    # treated as theft and revokes every session of the user. 0 disables.
    refresh_reuse_grace_seconds: int = 30
    # How many retries of one rotation the time window above may answer.
    # Each answer carries a fresh access token, so the window must not be an
    # unlimited minting source for whoever else holds the old token. Three
    # covers a lost response plus a couple of tabs racing on a platform
    # without cross-tab locks; past it the retry counts as reuse.
    refresh_reuse_grace_max_replays: int = 3
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
    enable_push_scheduler: bool = False
    # Master switch for Google/Apple sign-in. Off by default: /auth/social
    # and /auth/social/link answer 503 until it is true AND the provider's
    # audience list below is non-empty. Apple in particular needs a real
    # domain with HTTPS (see docs/SOCIAL_SIGN_IN.md).
    social_sign_in_enabled: bool = False
    # Lifetime of a server-issued sign-in nonce (POST /auth/social/nonce).
    social_nonce_ttl_seconds: int = 600
    # Nonces per minute per IP. A sign-in or link page asks for one on load
    # and again before each expires, so a school, office or carrier network
    # sharing one address needs more room than the refresh limit gives.
    # Each nonce is a small row that expires with the TTL above.
    social_nonce_rate_limit_max: int = 60
    google_oauth_client_ids: str = ""
    apple_audience_ids: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
    @property
    def google_oauth_client_id_set(self): return {x.strip() for x in self.google_oauth_client_ids.split(",") if x.strip()}
    @property
    def apple_audience_id_set(self): return {x.strip() for x in self.apple_audience_ids.split(",") if x.strip()}

@lru_cache
def get_settings(): return Settings()
