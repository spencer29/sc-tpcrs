from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import (
    IncidentAssign,
    IncidentCreate,
    IncidentDetailOut,
    IncidentNote,
    IncidentOut,
    IncidentStatusUpdate,
    NotificationOut,
    TimelineEntryOut,
)
from ..services import events, incident_service
from ..services.serialize import to_incident_out

router = APIRouter(prefix="/incidents", tags=["incidents"])

# Opening/triaging incidents is a responder action; ciso/admin/risk_officer own
# it. Compliance managers get read access (they consume incidents, not drive
# response) -- gated by get_current_user on the read routes.
_WRITER = require_role("risk_officer", "ciso", "admin")


@router.get("", response_model=list[IncidentOut])
async def list_incidents(
    vendor_id: uuid.UUID | None = None,
    status: str | None = Query(None, pattern="^(open|investigating|contained|resolved|closed)$"),
    severity: str | None = Query(None, pattern="^(Critical|High|Medium|Low)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[IncidentOut]:
    rows = await incident_service.list_incidents(
        db, vendor_id=vendor_id, status=status, severity=severity, limit=limit
    )
    return [to_incident_out(r) for r in rows]


@router.post("", response_model=IncidentDetailOut, status_code=201)
async def create_incident(
    body: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> IncidentDetailOut:
    incident = await incident_service.create_incident(
        db,
        actor=user.sub,
        vendor_id=str(body.vendor_id),
        title=body.title,
        description=body.description,
        severity=body.severity,
        category=body.category,
        source="manual",
        personal_data_involved=body.personal_data_involved,
    )
    await db.commit()
    await db.refresh(incident)
    await events.publish_incident_event(incident, "incident.opened")
    return await _detail(db, incident.id)


@router.get("/{incident_id}", response_model=IncidentDetailOut)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> IncidentDetailOut:
    detail = await _detail(db, incident_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return detail


@router.post("/{incident_id}/status", response_model=IncidentDetailOut)
async def update_status(
    incident_id: uuid.UUID,
    body: IncidentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> IncidentDetailOut:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    try:
        await incident_service.transition_status(db, incident, target=body.status, actor=user.sub, note=body.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(incident)
    event = "incident.resolved" if incident.status == "resolved" else "incident.status_changed"
    await events.publish_incident_event(incident, event)
    return await _detail(db, incident_id)


@router.post("/{incident_id}/assign", response_model=IncidentDetailOut)
async def assign_incident(
    incident_id: uuid.UUID,
    body: IncidentAssign,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> IncidentDetailOut:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    await incident_service.assign_incident(db, incident, assignee=body.assignee, actor=user.sub, note=body.note)
    await db.commit()
    return await _detail(db, incident_id)


@router.post("/{incident_id}/notes", response_model=IncidentDetailOut)
async def add_note(
    incident_id: uuid.UUID,
    body: IncidentNote,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> IncidentDetailOut:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    await incident_service.add_note(db, incident, message=body.message, actor=user.sub)
    await db.commit()
    return await _detail(db, incident_id)


@router.get("/{incident_id}/timeline", response_model=list[TimelineEntryOut])
async def get_timeline(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[TimelineEntryOut]:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    rows = await incident_service.get_timeline(db, incident_id)
    return [TimelineEntryOut.model_validate(r) for r in rows]


@router.get("/{incident_id}/notifications", response_model=list[NotificationOut])
async def get_notifications(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[NotificationOut]:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    rows = await incident_service.get_notifications(db, incident_id)
    return [NotificationOut.model_validate(r) for r in rows]


async def _detail(db: AsyncSession, incident_id: uuid.UUID) -> IncidentDetailOut | None:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        return None
    timeline = await incident_service.get_timeline(db, incident_id)
    notes = await incident_service.get_notifications(db, incident_id)
    base = to_incident_out(incident)
    return IncidentDetailOut(
        **base.model_dump(),
        timeline=[TimelineEntryOut.model_validate(t) for t in timeline],
        notifications=[NotificationOut.model_validate(n) for n in notes],
    )
