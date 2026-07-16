from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sc_tpcrs_common.jwt_shared import (
    TokenPayload,
    create_access_token,
    create_mfa_bridge_token,
    decode_token,
    get_current_user,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..demo_users import DEMO_PASSWORD, DEMO_USERS
from ..models import User
from ..schemas import LoginRequest, MfaBridgeResponse, MfaVerifyRequest, TokenResponse, UserOut
from ..security import (
    current_totp_code,
    decrypt_mfa_secret,
    deterministic_totp_secret,
    encrypt_mfa_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)
from ..services.audit import record_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])

MFA_BRIDGE_TTL_SECONDS = 300


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.post("/login", response_model=MfaBridgeResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> MfaBridgeResponse:
    user = await _get_user_by_email(db, payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = create_mfa_bridge_token(subject=user.email, ttl_seconds=MFA_BRIDGE_TTL_SECONDS)
    await record_audit_event(db, actor=user.email, action="LOGIN_PASSWORD_OK", resource=f"user:{user.id}")
    await db.commit()
    return MfaBridgeResponse(mfa_bridge_token=token, expires_in=MFA_BRIDGE_TTL_SECONDS)


@router.post("/mfa/verify", response_model=TokenResponse)
async def verify_mfa(payload: MfaVerifyRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    claims = decode_token(payload.mfa_bridge_token, expected_type="mfa_bridge")
    user = await _get_user_by_email(db, claims["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    raw_secret = decrypt_mfa_secret(user.mfa_secret_enc)
    if not verify_totp_code(raw_secret, payload.otp_code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")
    ttl_minutes = settings.jwt_access_ttl_minutes
    access_token = create_access_token(
        subject=user.email, role=user.role, mfa_verified=True, ttl_minutes=ttl_minutes
    )
    await record_audit_event(db, actor=user.email, action="LOGIN_MFA_OK", resource=f"user:{user.id}")
    await db.commit()
    return TokenResponse(
        access_token=access_token,
        role=user.role,
        sub=user.email,
        expires_in=ttl_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(current: TokenPayload = Depends(get_current_user)) -> UserOut:
    return UserOut(sub=current.sub, role=current.role, mfa_verified=current.mfa_verified)


@router.get("/dev/mfa-code")
async def dev_mfa_code(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Dev/demo convenience: return the current TOTP code for a user, so the
    demo doesn't require a real authenticator app. Disabled outside ENV=development."""
    if not settings.is_development:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    user = await _get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    raw_secret = decrypt_mfa_secret(user.mfa_secret_enc)
    return {"email": email, "otp_code": current_totp_code(raw_secret)}


@router.post("/dev/seed-users")
async def dev_seed_users(db: AsyncSession = Depends(get_db)) -> dict:
    """Idempotently creates the 8 demo users. Disabled outside ENV=development.

    Returns each demo user's login credentials so `seed/users.py` (or a
    developer curling this directly) can print them without needing a
    separate DB connection -- see `security.deterministic_totp_secret` for
    why the MFA secret doesn't need to be exported at all.
    """
    if not settings.is_development:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    created, existing = [], []
    for demo in DEMO_USERS:
        user = await _get_user_by_email(db, demo.email)
        if user is not None:
            existing.append(demo.email)
            continue
        raw_secret = deterministic_totp_secret(demo.email)
        db.add(
            User(
                email=demo.email,
                full_name=demo.full_name,
                password_hash=hash_password(DEMO_PASSWORD),
                role=demo.role,
                mfa_secret_enc=encrypt_mfa_secret(raw_secret),
                mfa_enabled=True,
                is_active=True,
            )
        )
        created.append(demo.email)
    if created:
        await record_audit_event(
            db, actor="system:seed", action="SEED_DEMO_USERS", resource="users", details={"created": created}
        )
    await db.commit()
    return {"created": created, "already_existed": existing, "password": DEMO_PASSWORD}
