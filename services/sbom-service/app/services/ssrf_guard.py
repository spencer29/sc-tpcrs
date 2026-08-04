"""SSRF guard for SBOM external-reference URLs (Module 3 security requirement).

CycloneDX `externalReferences` and SPDX `DownloadLocation`/`ExternalRef` fields
can contain arbitrary URLs. If the ingestion pipeline ever dereferences one
(to enrich a component), an attacker who can submit an SBOM could coerce the
service into fetching internal-only addresses (cloud metadata endpoints,
localhost admin ports, RFC1918 hosts) -- classic SSRF.

Policy here is deny-by-default and defence in depth:
  1. External refs are NOT fetched at all unless SBOM_FETCH_EXTERNAL_REFS=true.
  2. Even then, only https/http URLs whose host is on an explicit allow-list
     (SBOM_REF_ALLOWED_HOSTS) may be dereferenced.
  3. Any URL that resolves to a loopback/private/link-local/reserved address --
     or uses a non-web scheme (file:, gopher:, etc.) -- is always rejected,
     even if its host string happens to be allow-listed (rebinding defence).

`is_ref_fetchable` is the single decision point; the pipeline records rejected
refs in the SBOM document's review_notes rather than silently dropping them.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from ..config import settings

_ALLOWED_SCHEMES = {"http", "https"}


def _allowed_hosts() -> set[str]:
    raw = settings.sbom_ref_allowed_hosts or ""
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _is_disallowed_ip(host: str) -> bool:
    """True if the host resolves to any non-public address (or fails to resolve)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Cannot resolve -> treat as disallowed (fail closed).
        return True
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return True
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def is_ref_fetchable(url: str) -> tuple[bool, str]:
    """Return (allowed, reason). `reason` explains a rejection for audit/review."""
    if not settings.sbom_fetch_external_refs:
        return False, "external-reference fetching disabled (SBOM_FETCH_EXTERNAL_REFS=false)"

    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return False, f"scheme '{parsed.scheme}' not permitted"

    host = (parsed.hostname or "").lower()
    if not host:
        return False, "missing host"

    allowed = _allowed_hosts()
    if host not in allowed:
        return False, f"host '{host}' not in allow-list"

    if _is_disallowed_ip(host):
        return False, f"host '{host}' resolves to a private/loopback/reserved address"

    return True, "ok"
