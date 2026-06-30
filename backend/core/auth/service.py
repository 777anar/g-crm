import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import ForbiddenError, NotFoundError, UnauthenticatedError
from core.auth.models import User, UserCompanyRole
from core.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
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
    refresh_token = create_refresh_token(user_id=user.id)
    return access_token, refresh_token, memberships


def select_company(db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID) -> str:
    role_row = db.scalar(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == user_id, UserCompanyRole.company_id == company_id
        )
    )
    if role_row is None:
        raise ForbiddenError("You do not have access to this company")
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
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("User no longer active")
    return create_access_token(user_id=user.id, active_company_id=None, role=None)


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user
