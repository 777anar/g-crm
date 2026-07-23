"""TOTP-based staff MFA (Phase 18). A thin wrapper around `pyotp` so the rest
of `core/auth` never imports it directly -- if the underlying TOTP library
ever changes, this is the only file that needs to know.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from jose import jwt

from core.config import settings

_ISSUER = "G-STONE ERP"


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(*, secret: str, account_email: str) -> str:
    """An otpauth:// URI an authenticator app (Google Authenticator, Authy,
    1Password, ...) can scan or accept as manual entry -- issued once at
    /auth/mfa/setup, never persisted, since the secret it's derived from is
    already stored on the user row."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=_ISSUER)


def verify_code(*, secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)


def create_mfa_challenge_token(*, user_id: uuid.UUID) -> str:
    """A short-lived, single-purpose token identifying "this user passed
    password auth but still owes an MFA code" -- issued by /auth/login in
    place of real access/refresh tokens when `User.mfa_enabled` is set, and
    only ever accepted by /auth/mfa/verify. Kept separate from
    `create_access_token`/`create_refresh_token` (core/auth/security.py) via
    its own `type` claim so it can never be mistaken for (or misused as) a
    real session token."""
    payload = {
        "sub": str(user_id),
        "type": "mfa_challenge",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
