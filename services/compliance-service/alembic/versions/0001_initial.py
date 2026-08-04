"""initial compliance schema: compliance_assessments, control_results,
audit_log

Revision ID: 0001
Revises:
Create Date: 2026-08-03
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
        "compliance_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("framework", sa.String(64), nullable=False),
        sa.Column("compliance_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_controls", sa.Integer, nullable=False),
        sa.Column("compliant_count", sa.Integer, nullable=False),
        sa.Column("partial_count", sa.Integer, nullable=False),
        sa.Column("gap_count", sa.Integer, nullable=False),
        sa.Column("critical_gap_count", sa.Integer, nullable=False),
        sa.Column("framework_scores", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("summary", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_compliance_assessments_vendor_id", "compliance_assessments", ["vendor_id"])
    op.create_index("ix_compliance_assessments_framework", "compliance_assessments", ["framework"])
    op.create_index("ix_compliance_assessments_created_at", "compliance_assessments", ["created_at"])

    op.create_table(
        "control_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", sa.String(64), nullable=False),
        sa.Column("framework", sa.String(64), nullable=False),
        sa.Column("reference", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(128), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("weight", sa.Integer, nullable=False, server_default="3"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_critical_gap", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("evidence", sa.Text, nullable=False, server_default=""),
        sa.Column("remediation", sa.Text, nullable=False, server_default=""),
    )
    op.create_index("ix_control_results_assessment_id", "control_results", ["assessment_id"])
    op.create_index("ix_control_results_vendor_id", "control_results", ["vendor_id"])
    op.create_index("ix_control_results_control_id", "control_results", ["control_id"])
    op.create_index("ix_control_results_framework", "control_results", ["framework"])
    op.create_index("ix_control_results_status", "control_results", ["status"])

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
    op.drop_index("ix_control_results_status", table_name="control_results")
    op.drop_index("ix_control_results_framework", table_name="control_results")
    op.drop_index("ix_control_results_control_id", table_name="control_results")
    op.drop_index("ix_control_results_vendor_id", table_name="control_results")
    op.drop_index("ix_control_results_assessment_id", table_name="control_results")
    op.drop_table("control_results")
    op.drop_index("ix_compliance_assessments_created_at", table_name="compliance_assessments")
    op.drop_index("ix_compliance_assessments_framework", table_name="compliance_assessments")
    op.drop_index("ix_compliance_assessments_vendor_id", table_name="compliance_assessments")
    op.drop_table("compliance_assessments")
