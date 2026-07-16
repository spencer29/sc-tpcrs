"""Path-prefix -> upstream service routing table.

Every request the gateway receives is `/api/{prefix}/...`; the prefix
selects the upstream base URL. The full path (including the prefix) is
forwarded unchanged, since each downstream service owns that same prefix as
its own router mount point (e.g. vendor-service's own routes start with
`/vendors`, matching gateway path `/api/vendors/...`).
"""

from __future__ import annotations

from .config import settings

ROUTE_TABLE: dict[str, str] = {
    "auth": settings.auth_service_url,
    "vendors": settings.vendor_service_url,
    "risk": settings.risk_service_url,
    "sbom": settings.sbom_service_url,
    "compliance": settings.compliance_service_url,
    "monitoring": settings.monitoring_service_url,
    "incidents": settings.incident_service_url,
}

# Paths (relative to /api/, no leading slash) reachable without a bearer token.
PUBLIC_PATHS: frozenset[str] = frozenset({"auth/login", "auth/mfa/verify"})


def resolve_upstream(path: str) -> tuple[str, str] | None:
    """`path` is everything after `/api/`, e.g. `vendors/123`.

    Returns `(base_url, prefix)`, or None if no service owns that prefix.
    """
    prefix = path.split("/", 1)[0]
    base = ROUTE_TABLE.get(prefix)
    if base is None:
        return None
    return base, prefix


def is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    # Dev-only convenience endpoints (mfa-code lookup, demo user seeding) --
    # each downstream service independently enforces its own ENV=development
    # guard, so exempting the gateway's auth check here is not a security hole.
    return path.startswith("auth/dev/")
