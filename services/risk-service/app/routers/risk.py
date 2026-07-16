from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import AnomalyFlag, RiskScoreHistory
from ..schemas import AnomalyOut, RiskScoreHistoryOut, RiskScoreOut
from ..services.audit import record_audit_event
from ..services.vrs_calculator import compute_for_vendor

router = APIRouter(prefix="/risk/vendors", tags=["risk"])


@router.post("/{vendor_id}/compute", response_model=RiskScoreOut, status_code=status.HTTP_201_CREATED)
async def compute_risk_score(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "ciso", "admin")),
) -> RiskScoreHistory:
    row, _anomaly = await compute_for_vendor(db, vendor_id)
    await record_audit_event(
        db,
        actor=user.sub,
        action="VRS_COMPUTED",
        resource=f"vendor:{vendor_id}",
        details={"vrs_score": float(row.vrs_score), "tier": row.tier},
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{vendor_id}", response_model=RiskScoreOut)
async def get_latest_risk_score(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> RiskScoreHistory:
    stmt = (
        select(RiskScoreHistory)
        .where(RiskScoreHistory.vendor_id == vendor_id)
        .order_by(RiskScoreHistory.computed_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No risk score computed for this vendor yet")
    return row


@router.get("/{vendor_id}/history", response_model=RiskScoreHistoryOut)
async def get_risk_score_history(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> RiskScoreHistoryOut:
    stmt = (
        select(RiskScoreHistory)
        .where(RiskScoreHistory.vendor_id == vendor_id)
        .order_by(RiskScoreHistory.computed_at.asc())
    )
    items = (await db.execute(stmt)).scalars().all()
    return RiskScoreHistoryOut(items=list(items))


@router.get("/{vendor_id}/anomaly", response_model=AnomalyOut)
async def get_latest_anomaly(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> AnomalyFlag:
    stmt = (
        select(AnomalyFlag)
        .where(AnomalyFlag.vendor_id == vendor_id)
        .order_by(AnomalyFlag.detected_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No anomaly evaluation found for this vendor")
    return row
