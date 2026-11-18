"""Creates the API. Run: uv run uvicorn vb.main:app --reload (from backend/)."""

from fastapi import FastAPI

from vb.accounts import api as accounts_api
from vb.accounts.auth import check_auth_config
from vb.core import health
from vb.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    check_auth_config(settings)  # refuses to start a prod app with the dev login
    app = FastAPI(title="Virtual Brain", version="0.1.0", description=f"Environment: {settings.environment}")
    app.include_router(health.router, prefix="/v1")
    app.include_router(accounts_api.router, prefix="/v1")
    return app


app = create_app()
