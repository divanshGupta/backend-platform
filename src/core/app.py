from fastapi import FastAPI

from src.core.config.settings import get_settings

# ROUTES
from src.modules.user.controller import router as user_router
from src.modules.user.controller import auth_router as auth_router
from src.apps.hospital.medicine.category_controller import router as category_router
from src.apps.hospital.supplier.supplier_controller import router as supplier_router
from src.apps.hospital.medicine.medicine_controller import router as medicine_router
from src.apps.hospital.medicine.stock_controller import router as stock_router
from src.apps.hospital.purchase.purchase_controller import router as purchase_router
from src.apps.hospital.dashboard.dashboard_controller import router as dashboard_router

from src.core.database import model_registry  # noqa: F401

# middleware
from src.core.middleware.audit_context import AuditContextMiddleware

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

    app.add_middleware(AuditContextMiddleware)
    """
    Order matters here in one subtle way: middleware registered with 
    add_middleware runs outermost-registered-last, 
    but since AuditContextMiddleware only sets IP (actor comes later, inside get_current_user) 
    and doesn't depend on any other middleware, it's safe as the only one right now regardless of position. 
    Worth revisiting if we have to add CORS or logging middleware later — those don't need to run before or after this one specifically.
    """

    app.include_router(user_router)
    app.include_router(auth_router)

    app.include_router(category_router)
    app.include_router(supplier_router)
    app.include_router(medicine_router)
    app.include_router(stock_router)
    app.include_router(purchase_router)
    app.include_router(dashboard_router)
    
    @app.get("/health", tags=["system"])
    def health_check() -> dict:
        return {"status": "ok", "environment": settings.environment}

    return app