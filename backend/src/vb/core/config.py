"""Settings, read from environment variables prefixed VB_ (or a .env file). Invalid values fail at startup."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads backend/.env, then the repo-root .env (when run from backend/); real environment variables win.
    model_config = SettingsConfigDict(env_prefix="VB_", env_file=("../.env", ".env"), extra="ignore")

    environment: str = "dev"  # dev | test | prod
    # Which database to use (portability rule P1). Default: the Docker database from compose.yaml.
    database_url: str = "postgresql+psycopg://vb:vb@localhost:5434/vb"

    # Language model. "fake": recorded replies, free (tests, CI). "claude_cli": the local claude CLI on your
    # Claude Code login (development only, no key). "anthropic": the real API (production, needs a key).
    llm_provider: Literal["fake", "claude_cli", "anthropic"] = "fake"
    anthropic_api_key: SecretStr | None = None  # VB_ANTHROPIC_API_KEY; SecretStr keeps it out of logs
    llm_default_model: str = "claude-haiku-4-5"
    llm_prompt_models: dict[str, str] = {}  # per prompt, e.g. {"tutor_items": "claude-sonnet-5"}

    # Who is asking. "dev": every request is one fixed local learner (development only; refused when
    # environment is prod). "cognito": real login (stage 3).
    auth_mode: Literal["dev", "cognito"] = "dev"
    dev_learner_email: str = "dev@localhost"

    # Web pages allowed to call this API from a browser (CORS). Default: the local web dev server only.
    # The extension doesn't need an entry: its manifest's host_permissions let it call the API directly.
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
