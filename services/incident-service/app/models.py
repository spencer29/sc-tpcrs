from __future__ import annotations

import uuid
from datetime import datetime

from sc_tpcrs_common.db_types import GUID
from sqlalchemy import JSON, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Incident(Base):
    """A third-party security incident under active response.

    Incidents are opened automatically from high/critical monitoring alerts
    (source='monitoring.alerts', source_ref=the alert id) or manually by an
    analyst. They carry a lifecycle (open -> investigating -> contained ->
    resolved -> closed), an SLA clock keyed off severity, and flags for the
    two Nigerian regulatory notification regimes (CBN material-incident report,
    NDPA/NDPR personal-data-breach notification). Every state change is written
    to the append-only IncidentTimeline and the hash-chained audit_log."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Human-friendly sequential reference (e.g. INC-000042), assigned on create.
    reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    # Logical FK to vendor-service's vendors.id (separate DB boundary, no FK).
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # Critical/High/Medium/Low
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)
    # SECURITY_POSTURE / THREAT_INTEL / VULNERABILITY / COMPLIANCE / RISK / DATA_BREACH / MANUAL
    category: Mapped[str] = mapped_column(String(48), nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(48), nullable=False, default="manual")  # monitoring.alerts / manual
    # Upstream identity (the monitoring alert id) -- dedups auto-open so a
    # re-published alert doesn't spawn a duplicate incident.
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requires_cbn_notification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_ndpa_notification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IncidentTimeline(Base):
    """Append-only activity log for an incident: creation, status transitions,
    analyst notes, assignment changes, and generated notifications. The
    incident's current state is the Incident row; this is its immutable history
    (same append-only convention as risk-service's score history)."""

    __tablename__ = "incident_timeline"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    # created / status_change / note / assignment / notification
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class IncidentNotification(Base):
    """A drafted regulatory breach/incident notification for an incident.

    Two regimes are modelled: CBN (Central Bank of Nigeria material-incident
    report, 24h) and NDPC (Nigeria Data Protection Commission personal-data
    breach notification under the NDPA/NDPR, 72h). Generated as a draft the
    responder reviews and submits; we record the deadline and submission state,
    not a real filing (documented deviation -- no live regulator integration)."""

    __tablename__ = "incident_notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    regulator: Mapped[str] = mapped_column(String(32), nullable=False)  # CBN / NDPC
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")  # draft / submitted
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
