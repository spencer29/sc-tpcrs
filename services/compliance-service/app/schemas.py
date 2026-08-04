from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ControlStatus = Literal["met", "partial", "gap", "not_applicable"]
AssessmentStatus = Literal["Compliant", "Partially Compliant", "Non-Compliant"]


# --- Control library (static reference data) ---
class ControlOut(BaseModel):
    control_id: str
    framework: str
    reference: str
    domain: str
    title: str
    objective: str
    weight: int
    tags: list[str]


class FrameworkSummaryOut(BaseModel):
    framework: str
    control_count: int


class ControlLibraryOut(BaseModel):
    total_controls: int
    frameworks: list[FrameworkSummaryOut]


# --- Assessment requests ---
class ControlOverrideIn(BaseModel):
    """Optional manual override of a control's assessed status -- lets a
    compliance manager record a real evidence review on top of the
    deterministic baseline."""

    control_id: str
    status: ControlStatus
    evidence: str = ""
    remediation: str = ""


class AssessmentRequest(BaseModel):
    vendor_id: uuid.UUID
    # A specific framework label, or "ALL" (default) for the whole library.
    framework: str = "ALL"
    overrides: list[ControlOverrideIn] = Field(default_factory=list)


# --- Assessment results ---
class ControlResultOut(BaseModel):
    control_id: str
    framework: str
    reference: str
    domain: str
    title: str
    weight: int
    status: ControlStatus
    is_critical_gap: bool
    evidence: str
    remediation: str

    model_config = {"from_attributes": True}


class AssessmentOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    framework: str
    compliance_score: float
    status: AssessmentStatus
    total_controls: int
    compliant_count: int
    partial_count: int
    gap_count: int
    critical_gap_count: int
    framework_scores: dict
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DomainGapOut(BaseModel):
    domain: str
    framework: str
    total: int
    met: int
    partial: int
    gap: int
    not_applicable: int
    score: float


class GapAnalysisOut(BaseModel):
    assessment_id: uuid.UUID
    vendor_id: uuid.UUID
    framework: str
    compliance_score: float
    status: AssessmentStatus
    by_domain: list[DomainGapOut]
    # The remediation-ranked list of failing controls (critical gaps first).
    gaps: list[ControlResultOut]


class RegulatoryReportOut(BaseModel):
    """Regulator-ready report payload: assessment header + attestation-style
    framework roll-up + the full control register + prioritised gaps."""

    generated_at: datetime
    vendor_id: uuid.UUID
    framework: str
    assessment: AssessmentOut
    framework_breakdown: list[DomainGapOut]
    control_register: list[ControlResultOut]
    prioritised_gaps: list[ControlResultOut]
    attestation: str


class AssessmentListItemOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    framework: str
    compliance_score: float
    status: AssessmentStatus
    critical_gap_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceDashboardOut(BaseModel):
    total_assessments: int
    vendors_assessed: int
    average_score: float
    status_breakdown: dict[str, int]
    framework_coverage: dict[str, int]
    worst_vendors: list[AssessmentListItemOut]
