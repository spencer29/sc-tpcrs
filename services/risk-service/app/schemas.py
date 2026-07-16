from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Tier = Literal["Critical", "High", "Medium", "Low"]


class RiskScoreOut(BaseModel):
    vendor_id: uuid.UUID
    vrs_score: float
    questionnaire_score: float
    external_posture_score: float
    vulnerability_score: float
    breach_history_score: float
    threat_intel_score: float
    compliance_score: float
    tier: Tier
    computed_at: datetime

    model_config = {"from_attributes": True}


class RiskScoreHistoryOut(BaseModel):
    items: list[RiskScoreOut]


class AnomalyOut(BaseModel):
    vendor_id: uuid.UUID
    detected_at: datetime
    anomaly_score: float
    is_anomalous: bool
    model_version: str

    model_config = {"from_attributes": True}


class DashboardSummaryOut(BaseModel):
    tier_breakdown: dict[str, int]
    vrs_distribution: dict[str, int]
    top_risk_vendors: list[RiskScoreOut]
