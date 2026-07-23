import uuid
from typing import List

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AZN")
    locale: Mapped[str] = mapped_column(String, nullable=False, default="en")
    logo_url: Mapped[str] = mapped_column(String, nullable=True)
    enabled_modules: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    # Roles for which staff MFA is mandatory on this company (Phase 18's
    # "optional-then-mandatory-per-role" MFA control). Empty by default (MFA
    # stays opt-in); enforced at /auth/select-company, not at /auth/login,
    # since role is a per-company membership attribute.
    mfa_required_roles: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    def __repr__(self) -> str:
        return f"<Company {self.slug}>"
