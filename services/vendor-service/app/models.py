from __future__ import annotations

import uuid
from datetime import date, datetime

from sc_tpcrs_common.db_types import GUID
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

TIER_VALUES = ("Critical", "High", "Medium", "Low")
LIFECYCLE_STATES = (
    "INITIATED",
    "QUESTIONNAIRE_SENT",
    "QUESTIONNAIRE_COMPLETED",
    "ASSESSMENT_IN_PROGRESS",
    "ONBOARDED",
    "REJECTED",
)


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_entity_name: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(2))
    industry: Mapped[str | None] = mapped_column(String(100))
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(320))

    data_access_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    service_criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    integration_depth: Mapped[str] = mapped_column(String(20), nullable=False)
    overall_tier: Mapped[str] = mapped_column(String(20), nullable=False)

    onboarding_state: Mapped[str] = mapped_column(String(30), nullable=False, default="INITIATED")

    contract_start_date: Mapped[date | None] = mapped_column(Date)
    contract_end_date: Mapped[date | None] = mapped_column(Date)

    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["VendorDocument"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    questionnaires: Mapped[list["Questionnaire"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )


class VendorDocument(Base):
    __tablename__ = "vendor_documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("vendors.id", ondelete="CASCADE"))
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column()
    uploaded_by: Mapped[str | None] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor: Mapped[Vendor] = relationship(back_populates="documents")


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("vendors.id", ondelete="CASCADE"))
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SENT")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor: Mapped[Vendor] = relationship(back_populates="questionnaires")
    responses: Mapped[list["QuestionnaireResponse"]] = relationship(
        back_populates="questionnaire", cascade="all, delete-orphan"
    )


class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questionnaires.id", ondelete="CASCADE")
    )
    domain: Mapped[str] = mapped_column(String(150), nullable=False)
    question_code: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    answer: Mapped[str | None] = mapped_column(String(10))
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    questionnaire: Mapped[Questionnaire] = relationship(back_populates="responses")


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
