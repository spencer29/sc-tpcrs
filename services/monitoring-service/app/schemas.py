from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

Severity = Literal["Critical", "High", "Medium", "Low"]
AlertStatus = Literal["open", "acknowledged", "resolved"]


class SnapshotOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    posture_score: float
    open_service_count: int
    ioc_match_count: int
    abuse_report_count: int
    exposure_index: float
    drift: float
    observed_at: datetime

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    alert_type: str
    severity: Severity
    title: str
    description: str
    status: AlertStatus
    source: str
    details: dict
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertAckIn(BaseModel):
    note: str = ""


class SweepResult(BaseModel):
    vendors_swept: int
    snapshots_written: int
    alerts_opened: int
    alerts_updated: int
    duration_ms: float


class MonitoringDashboardOut(BaseModel):
    vendors_monitored: int
    open_alerts: int
    open_by_severity: dict[str, int]
    open_by_type: dict[str, int]
    average_exposure_index: float
    worst_vendors: list[SnapshotOut]
    recent_alerts: list[AlertOut]
