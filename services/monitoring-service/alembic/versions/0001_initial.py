"""initial monitoring schema: monitoring_snapshots, monitoring_alerts, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-08-04
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
        "monitoring_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("posture_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("open_service_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ioc_match_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("abuse_report_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("exposure_index", sa.Numeric(5, 2), nullable=False),
        sa.Column("drift", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("raw", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_monitoring_snapshots_vendor_id", "monitoring_snapshots", ["vendor_id"])
    op.create_index("ix_monitoring_snapshots_observed_at", "monitoring_snapshots", ["observed_at"])

    op.create_table(
        "monitoring_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(48), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("dedup_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("source", sa.String(48), nullable=False, server_default="sweep"),
        sa.Column("details", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("occurrence_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged_by", sa.String(255), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_monitoring_alerts_vendor_id", "monitoring_alerts", ["vendor_id"])
    op.create_index("ix_monitoring_alerts_alert_type", "monitoring_alerts", ["alert_type"])
    op.create_index("ix_monitoring_alerts_severity", "monitoring_alerts", ["severity"])
    op.create_index("ix_monitoring_alerts_dedup_key", "monitoring_alerts", ["dedup_key"])
    op.create_index("ix_monitoring_alerts_status", "monitoring_alerts", ["status"])
    op.create_index("ix_monitoring_alerts_last_seen_at", "monitoring_alerts", ["last_seen_at"])

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
    op.drop_index("ix_monitoring_alerts_last_seen_at", table_name="monitoring_alerts")
    op.drop_index("ix_monitoring_alerts_status", table_name="monitoring_alerts")
    op.drop_index("ix_monitoring_alerts_dedup_key", table_name="monitoring_alerts")
    op.drop_index("ix_monitoring_alerts_severity", table_name="monitoring_alerts")
    op.drop_index("ix_monitoring_alerts_alert_type", table_name="monitoring_alerts")
    op.drop_index("ix_monitoring_alerts_vendor_id", table_name="monitoring_alerts")
    op.drop_table("monitoring_alerts")
    op.drop_index("ix_monitoring_snapshots_observed_at", table_name="monitoring_snapshots")
    op.drop_index("ix_monitoring_snapshots_vendor_id", table_name="monitoring_snapshots")
    op.drop_table("monitoring_snapshots")
