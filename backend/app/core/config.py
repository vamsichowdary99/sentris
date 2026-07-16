from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration, sourced from environment variables / .env.

    See .env.example at the repo root for the full documented list.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    app_name: str = "Sentris"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-prod-use-a-long-random-string"
    cors_origins: str = "http://localhost:3000"

    database_url: str = (
        "postgresql+asyncpg://sentris_app:sentris_dev_password@db:5432/sentris"
    )
    database_migrator_url: str = (
        "postgresql+psycopg://sentris_migrator:sentris_dev_migrator_password@db:5432/sentris"
    )

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 14

    threat_intel_use_mock: bool = True
    virustotal_api_key: str | None = None
    abuseipdb_api_key: str | None = None
    shodan_api_key: str | None = None
    otx_api_key: str | None = None
    greynoise_api_key: str | None = None
    abusech_api_key: str | None = None
    urlscan_api_key: str | None = None
    investigate_cache_ttl_seconds: int = 3600
    investigate_provider_timeout_seconds: float = 12.0

    # --- AI layer (LiteLLM router) — free-first fallback chain, all optional ---
    nvidia_nim_api_key: str | None = None
    nvidia_nim_model: str = "meta/llama-3.3-70b-instruct"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    ai_request_timeout_seconds: float = 25.0
    ai_cache_ttl_seconds: int = 3600

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
