"""initial risk schema: risk_score_history, vendor_tech_stack,
anomaly_flags, audit_log

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
        "risk_score_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vrs_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("questionnaire_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("external_posture_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("vulnerability_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("breach_history_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("threat_intel_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("compliance_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("inputs_snapshot", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_risk_score_history_vendor_id", "risk_score_history", ["vendor_id"])
    op.create_index("ix_risk_score_history_computed_at", "risk_score_history", ["computed_at"])

    op.create_table(
        "vendor_tech_stack",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_name", sa.String(255), nullable=False),
        sa.Column("component_version", sa.String(100), nullable=False),
        sa.Column("ecosystem", sa.String(50), nullable=False, server_default="generic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vendor_tech_stack_vendor_id", "vendor_tech_stack", ["vendor_id"])

    op.create_table(
        "anomaly_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("anomaly_score", sa.Numeric(6, 5), nullable=False),
        sa.Column("is_anomalous", sa.Boolean, nullable=False),
        sa.Column("feature_snapshot", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("model_version", sa.String(50), nullable=False),
    )
    op.create_index("ix_anomaly_flags_vendor_id", "anomaly_flags", ["vendor_id"])

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
    op.drop_index("ix_anomaly_flags_vendor_id", table_name="anomaly_flags")
    op.drop_table("anomaly_flags")
    op.drop_index("ix_vendor_tech_stack_vendor_id", table_name="vendor_tech_stack")
    op.drop_table("vendor_tech_stack")
    op.drop_index("ix_risk_score_history_computed_at", table_name="risk_score_history")
    op.drop_index("ix_risk_score_history_vendor_id", table_name="risk_score_history")
    op.drop_table("risk_score_history")
