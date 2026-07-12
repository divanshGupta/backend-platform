from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.packages.audit.context import set_ip


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else None
        set_ip(ip)
        return await call_next(request)