"""Configuration: all environment-specific settings come from env vars (see .env.example)."""
import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_timeout_s: float = 30.0
    http_retries: int = 3
    chunk_days: int = 1
    cache_dir: str = "app/data/cache"
   
    default_cutoff_local: str = "09:20"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # Pilot scope: January 2026 delivery periods only.
    window_start: str = "2026-01-01"
    window_end: str = "2026-01-31"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
