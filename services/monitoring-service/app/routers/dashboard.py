from __future__ import annotations

from fastapi import APIRouter, Depends
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import AlertOut, MonitoringDashboardOut, SnapshotOut
from ..services import sweep_service

router = APIRouter(prefix="/monitoring/dashboard", tags=["monitoring-dashboard"])


@router.get("", response_model=MonitoringDashboardOut)
async def monitoring_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> MonitoringDashboardOut:
    """Portfolio-wide monitoring posture: latest snapshot per vendor + open-alert
    roll-ups. Aggregates over this service's own rows (same convention as the
    risk/compliance dashboards)."""
    latest = await sweep_service.latest_snapshot_per_vendor(db)
    open_alerts = await sweep_service.list_alerts(db, limit=500)
    open_only = [a for a in open_alerts if a.status != "resolved"]

    open_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    open_by_type: dict[str, int] = {}
    for a in open_only:
        open_by_severity[a.severity] = open_by_severity.get(a.severity, 0) + 1
        open_by_type[a.alert_type] = open_by_type.get(a.alert_type, 0) + 1

    avg_exposure = (
        round(sum(float(s.exposure_index) for s in latest) / len(latest), 2) if latest else 0.0
    )
    worst = sorted(latest, key=lambda s: float(s.exposure_index), reverse=True)[:5]
    recent = sorted(open_only, key=lambda a: a.last_seen_at, reverse=True)[:10]

    return MonitoringDashboardOut(
        vendors_monitored=len(latest),
        open_alerts=len(open_only),
        open_by_severity=open_by_severity,
        open_by_type=open_by_type,
        average_exposure_index=avg_exposure,
        worst_vendors=[SnapshotOut.model_validate(s) for s in worst],
        recent_alerts=[AlertOut.model_validate(a) for a in recent],
    )
