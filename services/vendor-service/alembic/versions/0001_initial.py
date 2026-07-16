"""initial vendor schema: vendors, vendor_documents, questionnaires,
questionnaire_responses, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-07-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_entity_name", sa.String(255)),
        sa.Column("country", sa.String(2)),
        sa.Column("industry", sa.String(100)),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("contact_email", sa.String(320)),
        sa.Column("data_access_scope", sa.String(20), nullable=False),
        sa.Column("service_criticality", sa.String(20), nullable=False),
        sa.Column("integration_depth", sa.String(20), nullable=False),
        sa.Column("overall_tier", sa.String(20), nullable=False),
        sa.Column("onboarding_state", sa.String(30), nullable=False, server_default="INITIATED"),
        sa.Column("contract_start_date", sa.Date),
        sa.Column("contract_end_date", sa.Date),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vendors_overall_tier", "vendors", ["overall_tier"])
    op.create_index("ix_vendors_onboarding_state", "vendors", ["onboarding_state"])

    op.create_table(
        "vendor_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100)),
        sa.Column("size_bytes", sa.Integer),
        sa.Column("uploaded_by", sa.String(255)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "questionnaires",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="SENT"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "questionnaire_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "questionnaire_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questionnaires.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(150), nullable=False),
        sa.Column("question_code", sa.String(20), nullable=False),
        sa.Column("question_text", sa.String(1000), nullable=False),
        sa.Column("answer", sa.String(10)),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(255), nullable=False),
        sa.Column("details", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.String(64), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("questionnaire_responses")
    op.drop_table("questionnaires")
    op.drop_table("vendor_documents")
    op.drop_index("ix_vendors_onboarding_state", table_name="vendors")
    op.drop_index("ix_vendors_overall_tier", table_name="vendors")
    op.drop_table("vendors")
