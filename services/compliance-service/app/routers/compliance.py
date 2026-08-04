from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy.ext.asyncio import AsyncSession

from ..control_library import ALL_FRAMEWORKS
from ..db import get_db
from ..schemas import (
    AssessmentListItemOut,
    AssessmentOut,
    AssessmentRequest,
    ControlResultOut,
    DomainGapOut,
    GapAnalysisOut,
    RegulatoryReportOut,
)
from ..services import assessment_service
from ..services.audit import record_audit_event
from ..services.events import publish_assessment_event
from ..services.reporting import build_report

router = APIRouter(prefix="/compliance/assessments", tags=["compliance"])

# Compliance writes are gated to compliance managers (and CISO/admin);
# reads are open to any authenticated user (defense-in-depth: gateway checks
# the JWT, we re-check the role here).
_WRITER = require_role("compliance_manager", "ciso", "admin")


def _validate_framework(framework: str) -> None:
    if framework != "ALL" and framework not in ALL_FRAMEWORKS:
        raise HTTPException(
            status_code=422,
            detail=f"unknown framework '{framework}'. Valid: ALL, {', '.join(ALL_FRAMEWORKS)}",
        )


@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(_WRITER),
) -> AssessmentOut:
    _validate_framework(body.framework)
    assessment = await assessment_service.run_assessment(
        db,
        vendor_id=body.vendor_id,
        framework=body.framework,
        overrides=[o.model_dump() for o in body.overrides],
        actor=user.sub,
    )
    await record_audit_event(
        db,
        actor=user.sub,
        action="COMPLIANCE_ASSESSED",
        resource=f"vendor:{body.vendor_id}",
        details={
            "assessment_id": str(assessment.id),
            "framework": body.framework,
            "compliance_score": float(assessment.compliance_score),
            "status": assessment.status,
            "critical_gap_count": assessment.critical_gap_count,
        },
    )
    await db.commit()
    await db.refresh(assessment)
    await publish_assessment_event(assessment)
    return AssessmentOut.model_validate(assessment)


@router.get("", response_model=list[AssessmentListItemOut])
async def list_assessments(
    vendor_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[AssessmentListItemOut]:
    rows = await assessment_service.list_assessments(db, vendor_id=vendor_id, limit=limit)
    return [AssessmentListItemOut.model_validate(r) for r in rows]


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> AssessmentOut:
    assessment = await assessment_service.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return AssessmentOut.model_validate(assessment)


@router.get("/{assessment_id}/gap-analysis", response_model=GapAnalysisOut)
async def gap_analysis(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> GapAnalysisOut:
    assessment = await assessment_service.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    rows = await assessment_service.control_results_for(db, assessment_id)
    report = build_report(assessment, rows)
    return GapAnalysisOut(
        assessment_id=assessment.id,
        vendor_id=assessment.vendor_id,
        framework=assessment.framework,
        compliance_score=float(assessment.compliance_score),
        status=assessment.status,
        by_domain=[DomainGapOut(**d) for d in report["framework_breakdown"]],
        gaps=[ControlResultOut.model_validate(r) for r in report["prioritised_gaps"]],
    )


@router.get("/{assessment_id}/report", response_model=RegulatoryReportOut)
async def regulatory_report(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> RegulatoryReportOut:
    assessment = await assessment_service.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    rows = await assessment_service.control_results_for(db, assessment_id)
    report = build_report(assessment, rows)
    return RegulatoryReportOut(
        generated_at=report["generated_at"],
        vendor_id=assessment.vendor_id,
        framework=assessment.framework,
        assessment=AssessmentOut.model_validate(assessment),
        framework_breakdown=[DomainGapOut(**d) for d in report["framework_breakdown"]],
        control_register=[ControlResultOut.model_validate(r) for r in report["control_register"]],
        prioritised_gaps=[ControlResultOut.model_validate(r) for r in report["prioritised_gaps"]],
        attestation=report["attestation"],
    )


@router.get("/{assessment_id}/controls", response_model=list[ControlResultOut])
async def assessment_controls(
    assessment_id: uuid.UUID,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[ControlResultOut]:
    assessment = await assessment_service.get_assessment(db, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    rows = await assessment_service.control_results_for(db, assessment_id)
    if status_filter:
        rows = [r for r in rows if r.status == status_filter]
    return [ControlResultOut.model_validate(r) for r in rows]
