"""Fetches the vendor portfolio to sweep from vendor-service.

Fails soft: if vendor-service is unreachable the sweep simply finds no
vendors (returns an empty list) rather than raising -- a monitoring sweep
should never take the service down.
"""

from __future__ import annotations

import httpx

from ..config import settings
from .internal_auth import service_auth_header


async def list_vendor_ids(limit: int = 200) -> list[dict]:
    """Return [{id, name}] for up to `limit` vendors, newest first.

    Paginates vendor-service's list endpoint (max page size 100)."""
    collected: list[dict] = []
    page = 1
    page_size = 100
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            while len(collected) < limit:
                resp = await client.get(
                    f"{settings.vendor_service_url}/vendors",
                    params={"page": page, "size": page_size},
                    headers=service_auth_header(),
                )
                if resp.status_code != 200:
                    break
                body = resp.json()
                items = body.get("items", [])
                if not items:
                    break
                for v in items:
                    collected.append({"id": v["id"], "name": v.get("name", "")})
                total = body.get("total", 0)
                if page * page_size >= total:
                    break
                page += 1
    except httpx.HTTPError:
        return collected
    return collected[:limit]
