from __future__ import annotations

import uuid
from datetime import datetime

from sc_tpcrs_common.db_types import GUID
from sqlalchemy import JSON, Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class MonitoringSnapshot(Base):
    """Append-only continuous-monitoring observation for a vendor.

    Each sweep records one snapshot per monitored vendor: the current external
    security posture score (Shodan mock), open-service exposure, threat-intel
    IOC matches (MISP mock), and abuse reports (AbuseIPDB mock). The "current"
    posture for a vendor is the latest row (ORDER BY observed_at DESC LIMIT 1);
    drift is the delta against the previous row -- one table, no current/history
    sync bugs (same convention as risk-service's RiskScoreHistory)."""

    __tablename__ = "monitoring_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Logical FK to vendor-service's vendors.id (separate DB boundary, no FK).
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    posture_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    open_service_count: Mapped[int] = mapped_column(nullable=False, default=0)
    ioc_match_count: Mapped[int] = mapped_column(nullable=False, default=0)
    abuse_report_count: Mapped[int] = mapped_column(nullable=False, default=0)

    # Composite exposure index (0-100, higher = worse) derived from the above,
    # so the dashboard/drift logic has a single monotonic health number.
    exposure_index: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Point delta of exposure_index vs the vendor's previous snapshot (0 for a
    # vendor's first-ever snapshot). Positive = posture worsened.
    drift: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)

    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class MonitoringAlert(Base):
    """A continuous-monitoring finding that warrants attention.

    Generated either by a posture sweep (drift crossing a threshold, new
    exposed services) or by reacting to another service's Kafka event
    (a fresh critical CVE, a non-compliant assessment, a risk-anomaly).
    Has an acknowledge/resolve lifecycle and is published to MONITORING_ALERTS
    for incident-service (Module 6) to consume."""

    __tablename__ = "monitoring_alerts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    # e.g. POSTURE_DRIFT, NEW_EXPOSED_SERVICE, CRITICAL_CVE, COMPLIANCE_GAP,
    # RISK_ANOMALY, THREAT_INTEL_MATCH.
    alert_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # Critical/High/Medium/Low
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Dedup fingerprint: identical open findings collapse onto one row rather
    # than spamming a new alert every sweep. (vendor_id, dedup_key) is unique
    # among OPEN alerts -- see alert_engine.upsert_alert.
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)  # open/acknowledged/resolved
    source: Mapped[str] = mapped_column(String(48), nullable=False, default="sweep")  # sweep/<kafka-topic>
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    occurrence_count: Mapped[int] = mapped_column(nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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
