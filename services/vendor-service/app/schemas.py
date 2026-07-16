from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Tier = Literal["Critical", "High", "Medium", "Low"]
LifecycleState = Literal[
    "INITIATED", "QUESTIONNAIRE_SENT", "QUESTIONNAIRE_COMPLETED", "ASSESSMENT_IN_PROGRESS", "ONBOARDED", "REJECTED"
]


class VendorCreateRequest(BaseModel):
    name: str
    legal_entity_name: str | None = None
    country: str | None = Field(default=None, max_length=2)
    industry: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    data_access_scope: Tier
    service_criticality: Tier
    integration_depth: Tier
    contract_start_date: date | None = None
    contract_end_date: date | None = None


class VendorUpdateRequest(BaseModel):
    name: str | None = None
    legal_entity_name: str | None = None
    country: str | None = Field(default=None, max_length=2)
    industry: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    data_access_scope: Tier | None = None
    service_criticality: Tier | None = None
    integration_depth: Tier | None = None
    contract_start_date: date | None = None
    contract_end_date: date | None = None


class VendorOut(BaseModel):
    id: uuid.UUID
    name: str
    legal_entity_name: str | None
    country: str | None
    industry: str | None
    contact_name: str | None
    contact_email: str | None
    data_access_scope: Tier
    service_criticality: Tier
    integration_depth: Tier
    overall_tier: Tier
    onboarding_state: LifecycleState
    contract_start_date: date | None
    contract_end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VendorListResponse(BaseModel):
    items: list[VendorOut]
    page: int
    size: int
    total: int


class TransitionRequest(BaseModel):
    target_state: LifecycleState


class QuestionOut(BaseModel):
    code: str
    domain: str
    text: str
    answer: str | None = None
    score: float | None = None


class QuestionnaireOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    tier: Tier
    status: Literal["SENT", "IN_PROGRESS", "COMPLETED"]
    sent_at: datetime | None
    completed_at: datetime | None
    questions: list[QuestionOut]


class QuestionnaireResponseIn(BaseModel):
    question_code: str
    answer: Literal["YES", "NO", "PARTIAL", "NA"]


class QuestionnaireResponsesUpdateRequest(BaseModel):
    responses: list[QuestionnaireResponseIn]


class QuestionnaireScoreOut(BaseModel):
    score: float


class DocumentOut(BaseModel):
    id: uuid.UUID
    document_type: str
    file_name: str
    content_type: str | None
    size_bytes: int | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}
