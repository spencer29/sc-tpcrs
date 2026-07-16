from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Questionnaire, QuestionnaireResponse, Vendor
from ..schemas import (
    QuestionnaireOut,
    QuestionnaireResponsesUpdateRequest,
    QuestionnaireScoreOut,
    QuestionOut,
)
from ..services.audit import record_audit_event
from ..services.events import publish_lifecycle_event
from ..services.question_bank import questions_for_tier, score_for_answer
from ..services.state_machine import InvalidTransitionError, validate_transition

router = APIRouter(prefix="/vendors/{vendor_id}/questionnaire", tags=["questionnaires"])


async def _get_vendor_or_404(db: AsyncSession, vendor_id: uuid.UUID) -> Vendor:
    vendor = await db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return vendor


async def _latest_questionnaire_or_404(db: AsyncSession, vendor_id: uuid.UUID) -> Questionnaire:
    stmt = (
        select(Questionnaire)
        .where(Questionnaire.vendor_id == vendor_id)
        .order_by(Questionnaire.created_at.desc())
        .limit(1)
        .options(selectinload(Questionnaire.responses))
    )
    questionnaire = (await db.execute(stmt)).scalar_one_or_none()
    if questionnaire is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No questionnaire found for this vendor")
    return questionnaire


def _to_out(questionnaire: Questionnaire) -> QuestionnaireOut:
    questions = [
        QuestionOut(
            code=r.question_code,
            domain=r.domain,
            text=r.question_text,
            answer=r.answer,
            score=float(r.score) if r.score is not None else None,
        )
        for r in sorted(questionnaire.responses, key=lambda r: r.question_code)
    ]
    return QuestionnaireOut(
        id=questionnaire.id,
        vendor_id=questionnaire.vendor_id,
        tier=questionnaire.tier,
        status=questionnaire.status,
        sent_at=questionnaire.sent_at,
        completed_at=questionnaire.completed_at,
        questions=questions,
    )


@router.post("", response_model=QuestionnaireOut, status_code=status.HTTP_201_CREATED)
async def generate_questionnaire(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "admin")),
) -> QuestionnaireOut:
    vendor = await _get_vendor_or_404(db, vendor_id)
    try:
        validate_transition(vendor.onboarding_state, "QUESTIONNAIRE_SENT")
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    now = datetime.now(timezone.utc)
    questionnaire = Questionnaire(vendor_id=vendor_id, tier=vendor.overall_tier, status="SENT", sent_at=now)
    db.add(questionnaire)
    await db.flush()

    for q in questions_for_tier(vendor.overall_tier):
        db.add(
            QuestionnaireResponse(
                questionnaire_id=questionnaire.id, domain=q.domain, question_code=q.code, question_text=q.text
            )
        )

    from_state = vendor.onboarding_state
    vendor.onboarding_state = "QUESTIONNAIRE_SENT"
    await record_audit_event(
        db,
        actor=user.sub,
        action="QUESTIONNAIRE_GENERATED",
        resource=f"vendor:{vendor_id}",
        details={"questionnaire_id": str(questionnaire.id), "tier": vendor.overall_tier},
    )
    await db.commit()

    await publish_lifecycle_event(
        vendor_id=str(vendor_id), from_state=from_state, to_state="QUESTIONNAIRE_SENT", tier=vendor.overall_tier, actor=user.sub
    )

    questionnaire = await _latest_questionnaire_or_404(db, vendor_id)
    return _to_out(questionnaire)


@router.get("", response_model=QuestionnaireOut)
async def get_questionnaire(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> QuestionnaireOut:
    questionnaire = await _latest_questionnaire_or_404(db, vendor_id)
    return _to_out(questionnaire)


@router.put("/responses", response_model=QuestionnaireOut)
async def update_responses(
    vendor_id: uuid.UUID,
    payload: QuestionnaireResponsesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> QuestionnaireOut:
    vendor = await _get_vendor_or_404(db, vendor_id)
    questionnaire = await _latest_questionnaire_or_404(db, vendor_id)
    if questionnaire.status == "COMPLETED":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Questionnaire already completed")

    by_code = {r.question_code: r for r in questionnaire.responses}
    now = datetime.now(timezone.utc)
    for item in payload.responses:
        response = by_code.get(item.question_code)
        if response is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown question_code: {item.question_code}")
        response.answer = item.answer
        response.score = score_for_answer(item.answer)
        response.answered_at = now

    fully_answered = all(r.answer is not None for r in questionnaire.responses)
    if fully_answered:
        questionnaire.status = "COMPLETED"
        questionnaire.completed_at = now
        from_state = vendor.onboarding_state
        try:
            validate_transition(vendor.onboarding_state, "QUESTIONNAIRE_COMPLETED")
        except InvalidTransitionError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        vendor.onboarding_state = "QUESTIONNAIRE_COMPLETED"
    else:
        questionnaire.status = "IN_PROGRESS"
        from_state = None

    await record_audit_event(
        db,
        actor=user.sub,
        action="QUESTIONNAIRE_RESPONSES_UPDATED",
        resource=f"vendor:{vendor_id}",
        details={"questionnaire_id": str(questionnaire.id), "fully_answered": fully_answered},
    )
    await db.commit()

    if fully_answered and from_state is not None:
        await publish_lifecycle_event(
            vendor_id=str(vendor_id), from_state=from_state, to_state="QUESTIONNAIRE_COMPLETED", tier=vendor.overall_tier, actor=user.sub
        )

    questionnaire = await _latest_questionnaire_or_404(db, vendor_id)
    return _to_out(questionnaire)


@router.get("/score", response_model=QuestionnaireScoreOut)
async def get_questionnaire_score(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> QuestionnaireScoreOut:
    """Average score across answered, non-NA questions. Consumed by
    risk-service as the "questionnaire self-assessment" VRS category. If no
    scoreable answers exist yet, returns 0.0 (a vendor with no evidence is
    treated as maximally unproven, not skipped)."""
    questionnaire = await _latest_questionnaire_or_404(db, vendor_id)
    scores = [float(r.score) for r in questionnaire.responses if r.score is not None]
    if not scores:
        return QuestionnaireScoreOut(score=0.0)
    return QuestionnaireScoreOut(score=round(sum(scores) / len(scores), 2))
