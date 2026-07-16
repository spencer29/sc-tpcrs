from __future__ import annotations

import httpx
from fastapi import Request, Response

_client = httpx.AsyncClient(timeout=30.0)

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


async def forward(
    request: Request,
    base_url: str,
    downstream_path: str,
    *,
    user_id: str | None,
    user_role: str | None,
) -> Response:
    url = f"{base_url}/{downstream_path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS}
    if user_id is not None:
        headers["X-User-Id"] = user_id
    if user_role is not None:
        headers["X-User-Role"] = user_role
    body = await request.body()

    upstream_resp = await _client.request(
        request.method, url, headers=headers, params=request.query_params, content=body
    )
    response_headers = {k: v for k, v in upstream_resp.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS}
    return Response(content=upstream_resp.content, status_code=upstream_resp.status_code, headers=response_headers)
