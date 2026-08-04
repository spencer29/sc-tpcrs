from __future__ import annotations

import uuid
from datetime import datetime

from sc_tpcrs_common.db_types import GUID
from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ComplianceAssessment(Base):
    """One compliance assessment of a vendor against a single framework
    (or the full library). Append-only history: the "current" assessment for
    a (vendor, framework) pair is the latest row by created_at -- same
    single-table convention as risk-service, to avoid current/history drift."""

    __tablename__ = "compliance_assessments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Logical FK to vendor-service's vendors.id -- no DB-level FK across the
    # service/database boundary.
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    # A framework label from control_library.ALL_FRAMEWORKS, or "ALL" for a
    # library-wide assessment.
    framework: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    compliance_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # Compliant / Partially Compliant / Non-Compliant

    total_controls: Mapped[int] = mapped_column(Integer, nullable=False)
    compliant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    partial_count: Mapped[int] = mapped_column(Integer, nullable=False)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_gap_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Per-framework score roll-up + summary metadata for fast report rendering.
    framework_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class ControlResult(Base):
    """Per-control finding within an assessment. This is the gap-analysis
    grain: every control the assessment covered gets one row recording its
    status, so a report can drill from score -> framework -> individual gap."""

    __tablename__ = "control_results"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    control_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # met / partial / gap / not_applicable
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_critical_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remediation: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
