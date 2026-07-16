from __future__ import annotations

import uuid
from datetime import datetime

from sc_tpcrs_common.db_types import GUID
from sqlalchemy import JSON, Boolean, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class RiskScoreHistory(Base):
    """Append-only. The "current" VRS for a vendor is simply the latest row
    (ORDER BY computed_at DESC LIMIT 1) -- deliberately one table, not a
    separate "current" table, to avoid current/history sync bugs."""

    __tablename__ = "risk_score_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Logical FK to vendor-service's vendors.id -- no DB-level FK since it's
    # a separate database/service boundary.
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    vrs_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    questionnaire_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    external_posture_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    vulnerability_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    breach_history_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    threat_intel_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    compliance_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    inputs_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class VendorTechStack(Base):
    """Seed-populated stub standing in for real SBOM ingestion (sbom-service
    is deferred). A future pass replaces this table with
    SBOM_INGESTION_EVENTS consumption -- see SECURITY.md."""

    __tablename__ = "vendor_tech_stack"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_version: Mapped[str] = mapped_column(String(100), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flags"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    anomaly_score: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    is_anomalous: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feature_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)


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
