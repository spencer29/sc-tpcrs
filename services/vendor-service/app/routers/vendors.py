from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Vendor
from ..schemas import TransitionRequest, VendorCreateRequest, VendorListResponse, VendorOut, VendorUpdateRequest
from ..services.audit import record_audit_event
from ..services.events import publish_lifecycle_event
from ..services.state_machine import InvalidTransitionError, validate_transition
from ..services.tiering import compute_tier

router = APIRouter(prefix="/vendors", tags=["vendors"])


async def _get_vendor_or_404(db: AsyncSession, vendor_id: uuid.UUID) -> Vendor:
    vendor = await db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return vendor


@router.post("", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "admin")),
) -> Vendor:
    tier = compute_tier(payload.data_access_scope, payload.service_criticality, payload.integration_depth)
    vendor = Vendor(
        **payload.model_dump(exclude={"contact_email"}),
        contact_email=str(payload.contact_email) if payload.contact_email else None,
        overall_tier=tier,
        onboarding_state="INITIATED",
        created_by=user.sub,
    )
    db.add(vendor)
    await db.flush()
    await record_audit_event(
        db, actor=user.sub, action="VENDOR_CREATED", resource=f"vendor:{vendor.id}", details={"tier": tier}
    )
    await db.commit()
    await db.refresh(vendor)
    await publish_lifecycle_event(
        vendor_id=str(vendor.id), from_state="", to_state="INITIATED", tier=tier, actor=user.sub
    )
    return vendor


@router.get("", response_model=VendorListResponse)
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
    tier: str | None = Query(default=None),
    state: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> VendorListResponse:
    stmt = select(Vendor)
    if tier:
        stmt = stmt.where(Vendor.overall_tier == tier)
    if state:
        stmt = stmt.where(Vendor.onboarding_state == state)
    if search:
        stmt = stmt.where(Vendor.name.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Vendor.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(stmt)).scalars().all()
    return VendorListResponse(items=list(items), page=page, size=size, total=total)


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> Vendor:
    return await _get_vendor_or_404(db, vendor_id)


@router.patch("/{vendor_id}", response_model=VendorOut)
async def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "admin")),
) -> Vendor:
    vendor = await _get_vendor_or_404(db, vendor_id)
    updates = payload.model_dump(exclude_unset=True)
    if "contact_email" in updates and updates["contact_email"] is not None:
        updates["contact_email"] = str(updates["contact_email"])
    for field, value in updates.items():
        setattr(vendor, field, value)

    if any(k in updates for k in ("data_access_scope", "service_criticality", "integration_depth")):
        vendor.overall_tier = compute_tier(vendor.data_access_scope, vendor.service_criticality, vendor.integration_depth)

    await record_audit_event(
        db, actor=user.sub, action="VENDOR_UPDATED", resource=f"vendor:{vendor.id}", details=updates
    )
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.post("/{vendor_id}/transition", response_model=VendorOut)
async def transition_vendor(
    vendor_id: uuid.UUID,
    payload: TransitionRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "ciso", "admin")),
) -> Vendor:
    vendor = await _get_vendor_or_404(db, vendor_id)
    try:
        validate_transition(vendor.onboarding_state, payload.target_state)
    except InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    from_state = vendor.onboarding_state
    vendor.onboarding_state = payload.target_state
    await record_audit_event(
        db,
        actor=user.sub,
        action="VENDOR_LIFECYCLE_TRANSITION",
        resource=f"vendor:{vendor.id}",
        details={"from_state": from_state, "to_state": payload.target_state},
    )
    await db.commit()
    await db.refresh(vendor)
    await publish_lifecycle_event(
        vendor_id=str(vendor.id), from_state=from_state, to_state=payload.target_state, tier=vendor.overall_tier, actor=user.sub
    )
    return vendor
