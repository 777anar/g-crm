import uuid
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, ForbiddenError, NotFoundError, UnauthenticatedError
from core.auth import mfa
from core.auth.models import User, UserCompanyRole
from core.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from core.auth.token_denylist import token_denylist
from core.companies.models import Company


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise UnauthenticatedError("Invalid email or password")
    return user


def get_user_company_memberships(db: Session, *, user_id: uuid.UUID):
    rows = db.execute(
        select(UserCompanyRole, Company)
        .join(Company, Company.id == UserCompanyRole.company_id)
        .where(UserCompanyRole.user_id == user_id)
    ).all()
    return [(role.role, company) for role, company in rows]


def issue_login_tokens(db: Session, *, user: User):
    memberships = get_user_company_memberships(db, user_id=user.id)
    access_token = create_access_token(user_id=user.id, active_company_id=None, role=None)
    generation = token_denylist.current_generation(str(user.id))
    refresh_token = create_refresh_token(user_id=user.id, generation=generation)
    return access_token, refresh_token, memberships


def select_company(db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> str:
    role_row = db.scalar(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == user_id, UserCompanyRole.company_id == company_id
        )
    )
    if role_row is None:
        raise ForbiddenError("You do not have access to this company")
    company = db.get(Company, company_id)
    if company is not None and role_row.role in company.mfa_required_roles:
        user = db.get(User, user_id)
        if user is None or not user.mfa_enabled:
            raise ForbiddenError(
                f"This company requires MFA for the '{role_row.role}' role. "
                "Enable MFA (POST /auth/mfa/setup then /auth/mfa/enable) before selecting it."
            )
    access_token = create_access_token(
        user_id=user_id,
        active_company_id=company_id,
        role=role_row.role,
        module_permissions=role_row.module_permissions,
    )
    return access_token


def refresh_access_token(db: Session, *, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise UnauthenticatedError("Invalid or expired refresh token") from exc
    if payload.get("type") != "refresh":
        raise UnauthenticatedError("Token is not a refresh token")
    user_id = uuid.UUID(payload["sub"])
    if token_denylist.is_revoked(str(user_id), int(payload.get("gen", 0))):
        raise UnauthenticatedError("Refresh token has been revoked")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("User no longer active")
    return create_access_token(user_id=user.id, active_company_id=None, role=None)


def logout_everywhere(*, refresh_token: str) -> None:
    """Invalidates every refresh token issued to this user until they log
    in again, including ones the server has never seen since (see
    core/auth/token_denylist.py). Access tokens already in a client's hands
    keep working until their own short expiry -- consistent with the
    standard "revoke the refresh token, let the access token just expire"
    pattern given its 15-minute default TTL.

    Best-effort by design: an already-invalid/expired/malformed refresh
    token has nothing meaningful to revoke (it's already unusable, or
    natural expiry already handles it), so this silently no-ops rather
    than raising -- logout must never fail from the client's perspective,
    since the client always discards its local tokens regardless."""
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        return
    if payload.get("type") != "refresh":
        return
    token_denylist.revoke_all(payload["sub"])


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def begin_mfa_challenge(*, user: User) -> str:
    return mfa.create_mfa_challenge_token(user_id=user.id)


def verify_mfa_challenge(db: Session, *, mfa_token: str, code: str) -> User:
    try:
        payload = decode_token(mfa_token)
    except ValueError as exc:
        raise UnauthenticatedError("Invalid or expired MFA challenge") from exc
    if payload.get("type") != "mfa_challenge":
        raise UnauthenticatedError("Not an MFA challenge token")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active or not user.mfa_enabled:
        raise UnauthenticatedError("MFA challenge is no longer valid")
    if not mfa.verify_code(secret=user.mfa_secret, code=code):
        raise UnauthenticatedError("Invalid MFA code")
    return user


def setup_mfa(*, user: User) -> Tuple[str, str]:
    """Generates (and persists) a new TOTP secret for `user`, but does not
    enable MFA yet -- see enable_mfa. Calling this again before enabling
    replaces the pending secret, so an abandoned setup can always be redone."""
    secret = mfa.generate_secret()
    user.mfa_secret = secret
    uri = mfa.provisioning_uri(secret=secret, account_email=user.email)
    return secret, uri


def enable_mfa(*, user: User, code: str) -> None:
    if not user.mfa_secret:
        raise BusinessRuleViolationError("Call POST /auth/mfa/setup before enabling MFA")
    if not mfa.verify_code(secret=user.mfa_secret, code=code):
        raise UnauthenticatedError("Invalid MFA code")
    user.mfa_enabled = True


def disable_mfa(*, user: User, code: str) -> None:
    if not user.mfa_enabled:
        return
    if not mfa.verify_code(secret=user.mfa_secret, code=code):
        raise UnauthenticatedError("Invalid MFA code")
    user.mfa_enabled = False
    user.mfa_secret = None
