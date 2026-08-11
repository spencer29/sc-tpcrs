from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import SnapshotOut, SweepResult
from ..services import events, sweep_service

# Mounted under the /monitoring prefix the gateway forwards unchanged.
router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Triggering a portfolio sweep is a privileged operation.
_WRITER = require_role("risk_officer", "ciso", "admin")

# Manual sweeps advance a distinct epoch space so they can surface drift on
# demand without colliding with the scheduler's epochs.
_manual_epoch = 1_000_000


@router.post("/sweep", response_model=SweepResult, status_code=202)
async def trigger_sweep(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> SweepResult:
    global _manual_epoch
    _manual_epoch += 1
    result, touched = await sweep_service.run_sweep(db, actor=user.sub, sweep_epoch=_manual_epoch)
    await events.publish_alerts(touched)
    await db.commit()
    return result


@router.get("/snapshots", response_model=list[SnapshotOut])
async def latest_snapshots(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[SnapshotOut]:
    rows = await sweep_service.latest_snapshot_per_vendor(db)
    rows.sort(key=lambda s: float(s.exposure_index), reverse=True)
    return [SnapshotOut.model_validate(r) for r in rows]


@router.get("/vendors/{vendor_id}/snapshots", response_model=list[SnapshotOut])
async def vendor_snapshot_history(
    vendor_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[SnapshotOut]:
    rows = await sweep_service.vendor_snapshots(db, vendor_id, limit=limit)
    return [SnapshotOut.model_validate(r) for r in rows]
