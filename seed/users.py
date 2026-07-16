from __future__ import annotations

import httpx

from .config import AUTH_SERVICE_URL


def seed_users() -> dict:
    resp = httpx.post(f"{AUTH_SERVICE_URL}/auth/dev/seed-users", timeout=30.0)
    resp.raise_for_status()
    return resp.json()
