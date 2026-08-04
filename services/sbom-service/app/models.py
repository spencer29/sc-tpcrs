"""Relational schema for SBOM ingestion (Module 3).

Postgres is the source of truth for the component/vulnerability cross-
reference; Neo4j mirrors it as a traversable dependency graph. The blueprint's
`sbom_components` and `vulnerabilities` tables map here as SbomComponent and
Vulnerability, plus an SbomDocument header row per ingested SBOM so re-ingesting
the same vendor's SBOM is auditable and idempotent.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sc_tpcrs_common.db_types import GUID
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

SBOM_FORMATS = ("CycloneDX", "SPDX")

# SSVC (Stakeholder-Specific Vulnerability Categorization) decision outcomes,
# per CISA's simplified deployer tree. Derived in services/cve_scanner.py.
SSVC_PRIORITIES = ("Act", "Attend", "Track*", "Track")


class SbomDocument(Base):
    __tablename__ = "sbom_documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    sbom_format: Mapped[str] = mapped_column(String(20), nullable=False)
    spec_version: Mapped[str | None] = mapped_column(String(20))
    serialization: Mapped[str | None] = mapped_column(String(20))  # json / xml / tag-value
    document_name: Mapped[str | None] = mapped_column(String(255))

    component_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vulnerable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incomplete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Components whose PURL had to be synthesised or could not be resolved --
    # flagged for manual review per the Module 3 normalisation-preprocessor req.
    review_notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    ingested_by: Mapped[str | None] = mapped_column(String(255))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    components: Mapped[list["SbomComponent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class SbomComponent(Base):
    __tablename__ = "sbom_components"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sbom_documents.id", ondelete="CASCADE"), index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    ecosystem: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    purl: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    cpe: Mapped[str | None] = mapped_column(String(500))
    file_hash: Mapped[str | None] = mapped_column(String(128))
    # purl_synthesised = we had to build the PURL from name+version because the
    # SBOM omitted it -> lower confidence, surfaced for manual review.
    purl_synthesised: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    document: Mapped[SbomDocument] = relationship(back_populates="components")
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        back_populates="component", cascade="all, delete-orphan"
    )


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    component_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sbom_components.id", ondelete="CASCADE"), index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    cve_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(2000))
    cvss_score: Mapped[float | None] = mapped_column(Float)
    cvss_vector: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="None")
    kev_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    known_ransomware: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ssvc_priority: Mapped[str] = mapped_column(String(10), nullable=False, default="Track")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Open")

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    component: Mapped[SbomComponent] = relationship(back_populates="vulnerabilities")


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
