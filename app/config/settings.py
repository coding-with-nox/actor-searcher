from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseModel):
    timeout_seconds: float = 15.0
    max_retries: int = 3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "actor-searcher"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/actor_searcher"
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4.1-mini"
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    brave_api_key: str = Field(default="", alias="BRAVE_API_KEY")

    # Actor profile
    actor_profile_path: str = Field(default="actor_profile.yaml", alias="ACTOR_PROFILE_PATH")

    # Telegram bot (HITL)
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    telegram_enabled: bool = Field(default=False, alias="TELEGRAM_ENABLED")

    # Pipeline
    notification_top_n: int = Field(default=5, alias="NOTIFICATION_TOP_N")
    matching_batch_size: int = Field(default=20, alias="MATCHING_BATCH_SIZE")
    minimum_match_score: float = Field(default=0.3, alias="MINIMUM_MATCH_SCORE")

    # Admin
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")

    # Default search schedule (auto-created on first startup)
    default_search_interval_minutes: int = Field(default=360, alias="SEARCH_INTERVAL_MINUTES")

    # Backstage provider
    backstage_email: str = Field(default="", alias="BACKSTAGE_EMAIL")
    backstage_password: str = Field(default="", alias="BACKSTAGE_PASSWORD")
    backstage_enabled: bool = Field(default=False, alias="BACKSTAGE_ENABLED")
    backstage_max_listings: int = Field(default=50, alias="BACKSTAGE_MAX_LISTINGS")

    # Gmail IMAP provider
    gmail_imap_host: str = Field(default="imap.gmail.com", alias="GMAIL_IMAP_HOST")
    gmail_imap_port: int = Field(default=993, alias="GMAIL_IMAP_PORT")
    gmail_app_password: str = Field(default="", alias="GMAIL_APP_PASSWORD")
    gmail_address: str = Field(default="", alias="GMAIL_ADDRESS")
    gmail_casting_senders: str = Field(default="", alias="GMAIL_CASTING_SENDERS")
    gmail_enabled: bool = Field(default=False, alias="GMAIL_ENABLED")

    provider: ProviderSettings = ProviderSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
