from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, Response, status
from sc_tpcrs_common.redis_cache import RedisCache

from . import health
from .auth_middleware import authenticate
from .config import settings
from .proxy import forward
from .rate_limit import enforce_rate_limit
from .routing import is_public, resolve_upstream

app = FastAPI(title="SC-TPCRS gateway")
app.include_router(health.router)

cache = RedisCache(settings.redis_url)


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(full_path: str, request: Request) -> Response:
    resolved = resolve_upstream(full_path)
    if resolved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown route")
    base_url, _prefix = resolved

    public = is_public(full_path)
    user = None
    if not public:
        user = authenticate(request.headers.get("authorization"))
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid bearer token")

    is_login_path = full_path == "auth/login"
    identifier = user.sub if user is not None else (request.client.host if request.client else "unknown")
    bucket = "login" if is_login_path else "general"
    limit = settings.gateway_login_rate_limit_per_min if is_login_path else settings.gateway_rate_limit_per_min
    await enforce_rate_limit(cache, identifier=f"{bucket}:{identifier}", limit_per_min=limit)

    return await forward(
        request,
        base_url,
        full_path,
        user_id=user.sub if user is not None else None,
        user_role=user.role if user is not None else None,
    )
