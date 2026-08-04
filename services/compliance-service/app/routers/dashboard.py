from __future__ import annotations

from fastapi import APIRouter, Depends
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import ComplianceAssessment
from ..schemas import AssessmentListItemOut, ComplianceDashboardOut
from ..services import assessment_service

router = APIRouter(prefix="/compliance/dashboard", tags=["compliance-dashboard"])


@router.get("", response_model=ComplianceDashboardOut)
async def compliance_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> ComplianceDashboardOut:
    """Portfolio-wide compliance posture, aggregated over the *latest*
    assessment per vendor (mirrors risk-service's dashboard convention:
    aggregate over this service's own rows, don't fan out to other services)."""
    all_rows = await assessment_service.list_assessments(db, limit=1000)

    # Latest assessment per vendor (rows already sorted newest-first).
    latest: dict = {}
    for r in all_rows:
        if r.vendor_id not in latest:
            latest[r.vendor_id] = r

    latest_rows = list(latest.values())
    status_breakdown = {"Compliant": 0, "Partially Compliant": 0, "Non-Compliant": 0}
    framework_coverage: dict[str, int] = {}
    score_sum = 0.0
    for r in latest_rows:
        status_breakdown[r.status] = status_breakdown.get(r.status, 0) + 1
        framework_coverage[r.framework] = framework_coverage.get(r.framework, 0) + 1
        score_sum += float(r.compliance_score)

    avg = round(score_sum / len(latest_rows), 2) if latest_rows else 0.0

    # Total assessment count (all history, not just latest).
    total = await db.scalar(select(func.count()).select_from(ComplianceAssessment)) or 0

    worst = sorted(latest_rows, key=lambda r: float(r.compliance_score))[:5]

    return ComplianceDashboardOut(
        total_assessments=int(total),
        vendors_assessed=len(latest_rows),
        average_score=avg,
        status_breakdown=status_breakdown,
        framework_coverage=framework_coverage,
        worst_vendors=[AssessmentListItemOut.model_validate(r) for r in worst],
    )
