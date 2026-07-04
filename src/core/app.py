from fastapi import FastAPI

from src.core.config.settings import get_settings


def create_app() -> FastAPI:
    """
    Application factory.

    Why a factory instead of a bare `app = FastAPI()` at module level?
    A factory function lets us create fresh, independently-configured
    app instances — critical for testing (spin up an app with test
    settings/dependencies overridden) and for keeping startup logic
    in one auditable place instead of scattered at import time.
    """
    settings = get_settings()

    app = FastAPI(
        title="Backend Platform",
        version="0.1.0",
        debug=not settings.is_production,
    )

    @app.get("/health", tags=["system"])
    def health_check() -> dict:
        return {"status": "ok", "environment": settings.environment}

    return app