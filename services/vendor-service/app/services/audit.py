from __future__ import annotations

from sc_tpcrs_common.audit_log import GENESIS_HASH, build_audit_entry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog


async def record_audit_event(
    db: AsyncSession, *, actor: str, action: str, resource: str, details: dict | None = None
) -> None:
    result = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    last = result.scalar_one_or_none()
    prev_hash = last.hash if last is not None else GENESIS_HASH
    entry = build_audit_entry(prev_hash=prev_hash, actor=actor, action=action, resource=resource, details=details)
    db.add(AuditLog(**entry))
    await db.flush()
