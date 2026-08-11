from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import AlertAckIn, AlertOut
from ..services import sweep_service
from ..services.audit import record_audit_event

router = APIRouter(prefix="/monitoring/alerts", tags=["monitoring-alerts"])

_WRITER = require_role("risk_officer", "ciso", "admin")


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    vendor_id: uuid.UUID | None = None,
    status: str | None = Query(None, pattern="^(open|acknowledged|resolved)$"),
    severity: str | None = Query(None, pattern="^(Critical|High|Medium|Low)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[AlertOut]:
    rows = await sweep_service.list_alerts(
        db, vendor_id=vendor_id, status=status, severity=severity, limit=limit
    )
    return [AlertOut.model_validate(r) for r in rows]


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> AlertOut:
    alert = await sweep_service.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    body: AlertAckIn,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> AlertOut:
    alert = await sweep_service.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    if alert.status == "resolved":
        raise HTTPException(status_code=409, detail="alert already resolved")
    alert.status = "acknowledged"
    alert.acknowledged_by = user.sub
    alert.acknowledged_at = datetime.now(timezone.utc)
    await record_audit_event(
        db,
        actor=user.sub,
        action="ALERT_ACKNOWLEDGED",
        resource=f"alert:{alert_id}",
        details={"note": body.note},
    )
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: uuid.UUID,
    body: AlertAckIn,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> AlertOut:
    alert = await sweep_service.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    await record_audit_event(
        db,
        actor=user.sub,
        action="ALERT_RESOLVED",
        resource=f"alert:{alert_id}",
        details={"note": body.note},
    )
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)
