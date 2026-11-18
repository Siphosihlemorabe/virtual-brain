"""Settings, read from environment variables prefixed VB_ (or a .env file). Invalid values fail at startup."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VB_", env_file=".env", extra="ignore")

    environment: str = "dev"  # dev | test | prod
    # Which database to use (portability rule P1). Default: the Docker database from compose.yaml.
    database_url: str = "postgresql+psycopg://vb:vb@localhost:5434/vb"


@lru_cache
def get_settings() -> Settings:
    return Settings()
