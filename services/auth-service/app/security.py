"""Password hashing, MFA-secret encryption, and TOTP helpers.

`MFA_SECRET_ENC_KEY` in .env.example is a human-readable placeholder, not a
formally valid Fernet key (Fernet requires exactly 32 urlsafe-base64-encoded
raw bytes). Rather than requiring operators to generate a properly-formatted
key by hand, we deterministically derive a valid 32-byte Fernet key from
whatever string is configured via sha256 -- any non-empty secret works, and
rotating it is just changing the env var.
"""

from __future__ import annotations

import base64
import hashlib

import pyotp
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from sc_tpcrs_common.adapters.base import seeded_random

from .config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _fernet_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_fernet_key_from_secret(settings.mfa_secret_enc_key))


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def deterministic_totp_secret(identifier: str) -> str:
    """Reproducible base32 TOTP secret derived from `identifier` (e.g. an email).

    Used only for demo/seed users so `seed/users.py` can print the same
    secret this service will independently derive when creating that user --
    no export round-trip needed. Real user registration should use
    `generate_totp_secret()` instead.
    """
    rng = seeded_random("mfa-secret", identifier)
    raw = bytes(rng.randrange(256) for _ in range(20))
    return base64.b32encode(raw).decode("utf-8").rstrip("=")


def encrypt_mfa_secret(raw_secret: str) -> str:
    return _fernet().encrypt(raw_secret.encode("utf-8")).decode("utf-8")


def decrypt_mfa_secret(enc_secret: str) -> str:
    return _fernet().decrypt(enc_secret.encode("utf-8")).decode("utf-8")


def current_totp_code(raw_secret: str) -> str:
    return pyotp.TOTP(raw_secret).now()


def verify_totp_code(raw_secret: str, code: str) -> bool:
    return pyotp.TOTP(raw_secret).verify(code, valid_window=1)
