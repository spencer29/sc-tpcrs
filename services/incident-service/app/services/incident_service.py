"""Incident persistence + lifecycle orchestration.

Opens incidents (manually or auto from a monitoring alert), drives status
transitions with an append-only timeline, drafts regulatory notifications when
the incident warrants them, and provides the read/aggregate helpers the routers
and dashboard use. Does not own Kafka -- events.py publishes incident.events
after the caller commits."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Incident, IncidentNotification, IncidentTimeline
from . import lifecycle, notifications
from .audit import record_audit_event


async def _next_reference(db: AsyncSession) -> str:
    count = int(await db.scalar(select(func.count()).select_from(Incident)) or 0)
    return f"INC-{count + 1:06d}"


async def _add_timeline(
    db: AsyncSession,
    *,
    incident_id: uuid.UUID,
    event_type: str,
    actor: str,
    message: str = "",
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    db.add(
        IncidentTimeline(
            incident_id=incident_id,
            event_type=event_type,
            actor=actor,
            message=message,
            from_status=from_status,
            to_status=to_status,
        )
    )


async def _maybe_draft_notifications(
    db: AsyncSession, incident: Incident, *, actor: str
) -> None:
    """Draft the CBN and/or NDPC notifications the incident's flags require.

    Idempotent: skips a regulator that already has a draft for this incident."""
    existing = set(
        await db.scalars(
            select(IncidentNotification.regulator).where(
                IncidentNotification.incident_id == incident.id
            )
        )
    )
    vendor_name = f"vendor:{incident.vendor_id}"

    if incident.requires_cbn_notification and "CBN" not in existing:
        body = notifications.build_cbn_notification(
            reference=incident.reference,
            vendor_name=vendor_name,
            severity=incident.severity,
            category=incident.category,
            description=incident.description,
            opened_at=incident.opened_at,
        )
        db.add(
            IncidentNotification(
                incident_id=incident.id,
                regulator="CBN",
                status="draft",
                deadline_at=notifications.cbn_deadline(incident.opened_at),
                body=body,
            )
        )
        await _add_timeline(
            db,
            incident_id=incident.id,
            event_type="notification",
            actor=actor,
            message="CBN cyber-incident notification drafted (24h deadline).",
        )

    if incident.requires_ndpa_notification and "NDPC" not in existing:
        body = notifications.build_ndpc_notification(
            reference=incident.reference,
            vendor_name=vendor_name,
            severity=incident.severity,
            description=incident.description,
            opened_at=incident.opened_at,
        )
        db.add(
            IncidentNotification(
                incident_id=incident.id,
                regulator="NDPC",
                status="draft",
                deadline_at=notifications.ndpa_deadline(incident.opened_at),
                body=body,
            )
        )
        await _add_timeline(
            db,
            incident_id=incident.id,
            event_type="notification",
            actor=actor,
            message="NDPC personal-data-breach notification drafted (72h deadline).",
        )


async def create_incident(
    db: AsyncSession,
    *,
    actor: str,
    vendor_id: str,
    title: str,
    description: str,
    severity: str,
    category: str,
    source: str = "manual",
    source_ref: str | None = None,
    personal_data_involved: bool = False,
) -> Incident:
    """Create an incident, seed its timeline, and draft any required regulatory
    notifications. Does not commit -- caller owns the transaction."""
    now = datetime.now(timezone.utc)
    reference = await _next_reference(db)

    requires_cbn = lifecycle.severity_rank(severity) >= lifecycle.severity_rank("High")
    requires_ndpa = personal_data_involved or lifecycle.category_implies_data_breach(category)

    incident = Incident(
        reference=reference,
        vendor_id=uuid.UUID(str(vendor_id)),
        title=title,
        description=description,
        severity=severity,
        status="open",
        category=category,
        source=source,
        source_ref=source_ref,
        sla_due_at=lifecycle.sla_due_at(now, severity),
        requires_cbn_notification=requires_cbn,
        requires_ndpa_notification=requires_ndpa,
        opened_at=now,
    )
    db.add(incident)
    await db.flush()

    await _add_timeline(
        db,
        incident_id=incident.id,
        event_type="created",
        actor=actor,
        message=f"Incident opened ({severity}, {category}) from {source}.",
        to_status="open",
    )
    await _maybe_draft_notifications(db, incident, actor=actor)
    await record_audit_event(
        db,
        actor=actor,
        action="INCIDENT_OPENED",
        resource=f"incident:{incident.reference}",
        details={"severity": severity, "category": category, "source": source, "source_ref": source_ref},
    )
    return incident


async def find_by_source_ref(db: AsyncSession, source_ref: str) -> Incident | None:
    return await db.scalar(select(Incident).where(Incident.source_ref == source_ref).limit(1))


def _stamp_status_timestamps(incident: Incident, target: str, now: datetime) -> None:
    if target == "contained" and incident.contained_at is None:
        incident.contained_at = now
    elif target == "resolved" and incident.resolved_at is None:
        incident.resolved_at = now
    elif target == "closed" and incident.closed_at is None:
        incident.closed_at = now
        if incident.resolved_at is None:
            incident.resolved_at = now


async def transition_status(
    db: AsyncSession, incident: Incident, *, target: str, actor: str, note: str = ""
) -> Incident:
    """Move an incident to `target`. Raises ValueError on an illegal transition.
    Does not commit."""
    current = incident.status
    if target == current:
        raise ValueError(f"incident already {current}")
    if not lifecycle.can_transition(current, target):
        raise ValueError(f"illegal transition {current} -> {target}")

    now = datetime.now(timezone.utc)
    incident.status = target
    _stamp_status_timestamps(incident, target, now)

    await _add_timeline(
        db,
        incident_id=incident.id,
        event_type="status_change",
        actor=actor,
        message=note or f"Status changed {current} -> {target}.",
        from_status=current,
        to_status=target,
    )
    await record_audit_event(
        db,
        actor=actor,
        action="INCIDENT_STATUS_CHANGED",
        resource=f"incident:{incident.reference}",
        details={"from": current, "to": target},
    )
    return incident


async def assign_incident(db: AsyncSession, incident: Incident, *, assignee: str, actor: str, note: str = "") -> Incident:
    prev = incident.assignee
    incident.assignee = assignee
    await _add_timeline(
        db,
        incident_id=incident.id,
        event_type="assignment",
        actor=actor,
        message=note or f"Assigned to {assignee}" + (f" (was {prev})" if prev else "") + ".",
    )
    await record_audit_event(
        db,
        actor=actor,
        action="INCIDENT_ASSIGNED",
        resource=f"incident:{incident.reference}",
        details={"assignee": assignee},
    )
    return incident


async def add_note(db: AsyncSession, incident: Incident, *, message: str, actor: str) -> Incident:
    await _add_timeline(
        db, incident_id=incident.id, event_type="note", actor=actor, message=message
    )
    await record_audit_event(
        db, actor=actor, action="INCIDENT_NOTE_ADDED", resource=f"incident:{incident.reference}"
    )
    return incident


# --- Read helpers ---
async def get_incident(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    return await db.get(Incident, incident_id)


async def get_timeline(db: AsyncSession, incident_id: uuid.UUID) -> list[IncidentTimeline]:
    return list(
        await db.scalars(
            select(IncidentTimeline)
            .where(IncidentTimeline.incident_id == incident_id)
            .order_by(IncidentTimeline.created_at.asc())
        )
    )


async def get_notifications(db: AsyncSession, incident_id: uuid.UUID) -> list[IncidentNotification]:
    return list(
        await db.scalars(
            select(IncidentNotification)
            .where(IncidentNotification.incident_id == incident_id)
            .order_by(IncidentNotification.created_at.asc())
        )
    )


async def list_incidents(
    db: AsyncSession,
    *,
    vendor_id: uuid.UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[Incident]:
    stmt = select(Incident)
    if vendor_id is not None:
        stmt = stmt.where(Incident.vendor_id == vendor_id)
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    if severity is not None:
        stmt = stmt.where(Incident.severity == severity)
    stmt = stmt.order_by(Incident.opened_at.desc()).limit(limit)
    return list(await db.scalars(stmt))


async def all_incidents(db: AsyncSession, limit: int = 1000) -> list[Incident]:
    return list(
        await db.scalars(select(Incident).order_by(Incident.opened_at.desc()).limit(limit))
    )


async def pending_notification_count(db: AsyncSession) -> int:
    return int(
        await db.scalar(
            select(func.count()).select_from(IncidentNotification).where(
                IncidentNotification.status == "draft"
            )
        )
        or 0
    )
