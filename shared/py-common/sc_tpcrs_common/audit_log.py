"""Hash-chained audit log helpers.

Pure functions so the chaining logic is provably correct via unit tests
independent of any particular service's SQLAlchemy models. Each service
stores its own audit_log table (actor, action, resource, details, recorded_at,
prev_hash, hash) and uses `build_audit_entry` to construct the next row after
reading the previous row's `hash` (or GENESIS_HASH if the table is empty).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

GENESIS_HASH = "0" * 64


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(prev_hash: str, entry: dict[str, Any]) -> str:
    material = f"{prev_hash}|{canonical_json(entry)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_audit_entry(
    *,
    prev_hash: str,
    actor: str,
    action: str,
    resource: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Returns a dict ready to persist as the next chained audit row."""
    base = {
        "actor": actor,
        "action": action,
        "resource": resource,
        "details": details or {},
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    entry_hash = compute_entry_hash(prev_hash, base)
    return {**base, "prev_hash": prev_hash, "hash": entry_hash}


def verify_chain(entries: list[dict[str, Any]]) -> bool:
    """entries must be chronologically ordered rows shaped like build_audit_entry's output."""
    prev = GENESIS_HASH
    for entry in entries:
        base = {k: v for k, v in entry.items() if k not in ("prev_hash", "hash")}
        expected_hash = compute_entry_hash(prev, base)
        if entry.get("prev_hash") != prev or entry.get("hash") != expected_hash:
            return False
        prev = entry["hash"]
    return True
