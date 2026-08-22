from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "CIVICHEAT AI"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False

    # FortyGuard
    fortyguard_api_key: str = ""
    fortyguard_base_url: str = "https://api.fortyguard.com"

    # Nemotron
    nemotron_base_url: str = ""
    nemotron_api_key: str = ""
    nemotron_model: str = "nvidia/llama-3.1-nemotron-nano-8b-v1"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
