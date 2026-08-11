from __future__ import annotations

from fastapi import APIRouter, Depends
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import IncidentDashboardOut
from ..services import incident_service
from ..services.lifecycle import is_sla_breached
from ..services.serialize import to_incident_out

router = APIRouter(prefix="/incidents/dashboard", tags=["incidents-dashboard"])

_ACTIVE = ("open", "investigating", "contained")


@router.get("", response_model=IncidentDashboardOut)
async def incident_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> IncidentDashboardOut:
    """Response posture roll-up over this service's own incident rows."""
    incidents = await incident_service.all_incidents(db)
    active = [i for i in incidents if i.status in _ACTIVE]

    open_by_severity: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    open_by_category: dict[str, int] = {}
    for i in active:
        open_by_severity[i.severity] = open_by_severity.get(i.severity, 0) + 1
        open_by_category[i.category] = open_by_category.get(i.category, 0) + 1

    sla_breached = sum(1 for i in active if is_sla_breached(i.sla_due_at, i.status))

    # Mean time to contain (hours) over incidents that reached containment.
    contained = [i for i in incidents if i.contained_at is not None]
    mttc = None
    if contained:
        total_hours = sum(
            (i.contained_at - i.opened_at).total_seconds() / 3600.0 for i in contained
        )
        mttc = round(total_hours / len(contained), 2)

    pending = await incident_service.pending_notification_count(db)

    return IncidentDashboardOut(
        total_incidents=len(incidents),
        open_incidents=len(active),
        open_by_severity=open_by_severity,
        open_by_category=open_by_category,
        sla_breached=sla_breached,
        pending_notifications=pending,
        mean_time_to_contain_hours=mttc,
        recent_incidents=[to_incident_out(i) for i in incidents[:10]],
    )
