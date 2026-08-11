from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["Critical", "High", "Medium", "Low"]
IncidentStatus = Literal["open", "investigating", "contained", "resolved", "closed"]
Category = Literal[
    "SECURITY_POSTURE",
    "THREAT_INTEL",
    "VULNERABILITY",
    "COMPLIANCE",
    "RISK",
    "DATA_BREACH",
    "MANUAL",
]


class IncidentCreate(BaseModel):
    vendor_id: uuid.UUID
    title: str = Field(min_length=3, max_length=255)
    description: str = ""
    severity: Severity = "Medium"
    category: Category = "MANUAL"
    # Explicit breach flag lets an analyst force NDPA notification even when the
    # category isn't DATA_BREACH (e.g. suspected exposure under investigation).
    personal_data_involved: bool = False


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    note: str = ""


class IncidentAssign(BaseModel):
    assignee: str = Field(min_length=1, max_length=255)
    note: str = ""


class IncidentNote(BaseModel):
    message: str = Field(min_length=1)


class TimelineEntryOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: str
    actor: str
    message: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    regulator: str
    status: str
    deadline_at: datetime
    body: str
    reference: Optional[str] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IncidentOut(BaseModel):
    id: uuid.UUID
    reference: str
    vendor_id: uuid.UUID
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    category: str
    source: str
    source_ref: Optional[str] = None
    assignee: Optional[str] = None
    sla_due_at: datetime
    sla_breached: bool = False
    requires_cbn_notification: bool
    requires_ndpa_notification: bool
    opened_at: datetime
    updated_at: datetime
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IncidentDetailOut(IncidentOut):
    timeline: list[TimelineEntryOut] = []
    notifications: list[NotificationOut] = []


class IncidentDashboardOut(BaseModel):
    total_incidents: int
    open_incidents: int
    open_by_severity: dict[str, int]
    open_by_category: dict[str, int]
    sla_breached: int
    pending_notifications: int
    mean_time_to_contain_hours: Optional[float] = None
    recent_incidents: list[IncidentOut]
