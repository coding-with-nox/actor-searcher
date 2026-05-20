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

    provider: ProviderSettings = ProviderSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
