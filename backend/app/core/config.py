from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Lingo² API"
    database_url: str = "postgresql+psycopg://lingosquared:change-me@db:5432/lingosquared"
    jwt_secret: str = "development-only-secret"
    access_token_expire_seconds: int = 86400
    admin_emails: str = "admin@example.com"
    enable_hearts: bool = False
    enable_gems: bool = False
    enable_leaderboard: bool = False
    cors_origins: str = "http://localhost:5173"
    # Raw service-account JSON content (not a file path) — set as a single
    # env var so credentials don't require a mounted file in every deploy
    # environment.
    google_cloud_tts_credentials_json: str = ""
    # Google's free tier for Standard voices is 4M characters/month.
    tts_monthly_char_budget: int = 4000000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admin_email_set(self): return {x.strip().lower() for x in self.admin_emails.split(",") if x.strip()}
    @property
    def cors_origin_list(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings(): return Settings()
