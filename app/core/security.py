import hmac
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status
from pydantic import SecretStr
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

PUBLIC_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")
SENSITIVE_PREFIXES = (
    "/database-health", "/worker-health", "/scheduler-health", "/generated",
    "/api/v1/dashboard", "/api/v1/automation", "/api/v1/providers", "/api/v1/reports",
    "/api/v1/posters", "/api/v1/predictions", "/api/v1/evaluation", "/api/v1/calibration",
)


def extract_admin_key(request: Request) -> str | None:
    header = request.headers.get("X-Admin-API-Key")
    if header:
        return header
    authorization = request.headers.get("Authorization", "")
    return authorization.removeprefix("Bearer ").strip() or None


def is_admin_key_valid(candidate: str | None, configured: SecretStr | None) -> bool:
    if candidate is None or configured is None:
        return configured is None
    return hmac.compare_digest(candidate.encode(), configured.get_secret_value().encode())


def require_admin(request: Request) -> None:
    configured = get_settings().admin_api_key
    if configured is not None and not is_admin_key_valid(extract_admin_key(request), configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrator authentication required")


class ProductionSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, rate_limit_requests: int, rate_limit_window_seconds: int):
        super().__init__(app)
        self._limit = rate_limit_requests
        self._window = rate_limit_window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        settings = get_settings()
        path = request.url.path
        public = any(path == prefix or path.startswith(prefix + "/") for prefix in PUBLIC_PREFIXES)
        sensitive = any(path == prefix or path.startswith(prefix + "/") for prefix in SENSITIVE_PREFIXES)
        must_auth = settings.admin_api_key is not None and (not public and (sensitive or request.method in {"POST", "PUT", "PATCH", "DELETE"}))
        if settings.app_env == "production" and settings.admin_api_key is None and (sensitive or request.method in {"POST", "PUT", "PATCH", "DELETE"}):
            return JSONResponse(status_code=503, content={"detail": "ADMIN_API_KEY is required in production"})
        if must_auth and not is_admin_key_valid(extract_admin_key(request), settings.admin_api_key):
            return JSONResponse(status_code=401, content={"detail": "Administrator authentication required"})
        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._requests[client_key]
        while window and now - window[0] > self._window:
            window.popleft()
        if len(window) >= self._limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}, headers={"Retry-After": str(self._window)})
        window.append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response
