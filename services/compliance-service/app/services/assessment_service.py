"""Orchestrates an assessment run: evaluate -> persist -> return ORM rows.

Kept separate from assessment_engine (pure, DB-free scoring/gap logic) so the
engine stays unit-testable without a database and this layer owns all the
SQLAlchemy I/O.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ComplianceAssessment, ControlResult
from . import assessment_engine as engine


async def run_assessment(
    db: AsyncSession,
    *,
    vendor_id: uuid.UUID,
    framework: str = "ALL",
    overrides: list[dict] | None = None,
    actor: str,
) -> ComplianceAssessment:
    """Evaluate the vendor against the framework and persist the assessment +
    per-control results. Does NOT commit -- the caller owns the transaction
    (so audit + event publication happen atomically with the write)."""
    override_map = {o["control_id"]: o for o in (overrides or [])}
    results = engine.evaluate_controls(str(vendor_id), framework, override_map)

    score = engine.compliance_score(results)
    status = engine.status_from_score(score)
    summary = engine.summarise(results)
    fw_scores = engine.framework_score_breakdown(results)

    assessment = ComplianceAssessment(
        vendor_id=vendor_id,
        framework=framework,
        compliance_score=score,
        status=status,
        total_controls=summary["total_controls"],
        compliant_count=summary["compliant_count"],
        partial_count=summary["partial_count"],
        gap_count=summary["gap_count"],
        critical_gap_count=summary["critical_gap_count"],
        framework_scores=fw_scores,
        summary=summary,
        created_by=actor,
    )
    db.add(assessment)
    await db.flush()  # populate assessment.id

    for r in results:
        db.add(
            ControlResult(
                assessment_id=assessment.id,
                vendor_id=vendor_id,
                control_id=r.spec.control_id,
                framework=r.spec.framework,
                reference=r.spec.reference,
                domain=r.spec.domain,
                title=r.spec.title,
                weight=r.spec.weight,
                status=r.status,
                is_critical_gap=r.is_critical_gap,
                evidence=r.evidence,
                remediation=r.remediation,
            )
        )
    await db.flush()
    return assessment


async def get_assessment(db: AsyncSession, assessment_id: uuid.UUID) -> ComplianceAssessment | None:
    return await db.get(ComplianceAssessment, assessment_id)


async def latest_assessment_for_vendor(
    db: AsyncSession, vendor_id: uuid.UUID, framework: str | None = None
) -> ComplianceAssessment | None:
    stmt = select(ComplianceAssessment).where(ComplianceAssessment.vendor_id == vendor_id)
    if framework:
        stmt = stmt.where(ComplianceAssessment.framework == framework)
    stmt = stmt.order_by(ComplianceAssessment.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def control_results_for(db: AsyncSession, assessment_id: uuid.UUID) -> list[ControlResult]:
    result = await db.execute(
        select(ControlResult).where(ControlResult.assessment_id == assessment_id)
    )
    return list(result.scalars().all())


async def list_assessments(
    db: AsyncSession, *, vendor_id: uuid.UUID | None = None, limit: int = 100
) -> list[ComplianceAssessment]:
    stmt = select(ComplianceAssessment)
    if vendor_id:
        stmt = stmt.where(ComplianceAssessment.vendor_id == vendor_id)
    stmt = stmt.order_by(ComplianceAssessment.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
