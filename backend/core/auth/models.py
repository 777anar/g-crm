from typing import Dict, Optional

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # TOTP-based MFA (Phase 18). `mfa_secret` is written once at /auth/mfa/setup
    # and only takes effect (mfa_enabled=True) once the user proves possession
    # of it via /auth/mfa/enable -- never enabled from the setup call alone,
    # so a setup request that's never completed leaves login unaffected.
    mfa_secret: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


ROLE_OWNER = "owner"
ROLE_MANAGER = "manager"
ROLE_REP = "rep"
ROLE_VIEWER = "viewer"
VALID_ROLES = {ROLE_OWNER, ROLE_MANAGER, ROLE_REP, ROLE_VIEWER}


class UserCompanyRole(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_company_roles"
    __table_args__ = (UniqueConstraint("user_id", "company_id", name="uq_user_company"),)

    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    module_permissions: Mapped[Dict] = mapped_column(JSON, nullable=False, default=dict)
