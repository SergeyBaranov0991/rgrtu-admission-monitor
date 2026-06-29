from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.max_webhook import router as max_webhook_router
from app.config import get_settings
from app.observability.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="RGRTU Admission Monitor", version="0.1.0")
    app.state.settings = settings
    app.include_router(health_router)
    app.include_router(max_webhook_router)
    return app


app = create_app()

