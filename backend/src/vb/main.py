"""Creates the API. Run: uv run uvicorn vb.main:app --reload (from backend/)."""

from fastapi import FastAPI

from vb.core import health
from vb.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Virtual Brain", version="0.1.0", description=f"Environment: {settings.environment}")
    app.include_router(health.router, prefix="/v1")
    return app


app = create_app()
