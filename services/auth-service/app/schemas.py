from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MfaBridgeResponse(BaseModel):
    mfa_bridge_token: str
    expires_in: int


class MfaVerifyRequest(BaseModel):
    mfa_bridge_token: str
    otp_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    sub: str
    expires_in: int


class UserOut(BaseModel):
    sub: str
    role: str
    mfa_verified: bool
