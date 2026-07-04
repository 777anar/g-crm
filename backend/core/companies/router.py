from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth.models import User, UserCompanyRole
from core.companies.models import Company
from core.companies.schemas import CompanyOut, CompanyUserOut
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, get_current_user, require_permission

router = APIRouter(prefix="/api/v1/core/companies", tags=["core:companies"])


@router.get("", response_model=List[CompanyOut])
def list_my_companies(
    db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
) -> List[CompanyOut]:
    rows = db.execute(
        select(Company)
        .join(UserCompanyRole, UserCompanyRole.company_id == Company.id)
        .where(UserCompanyRole.user_id == current_user.user_id)
    ).scalars().all()
    return [CompanyOut.model_validate(c) for c in rows]


@router.get("/users", response_model=List[CompanyUserOut])
def list_company_users(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("core:companies:read")),
) -> List[CompanyUserOut]:
    """Every user with a role on the active company -- used by module UIs
    that need to assign a person to something (crew members, managers, ...)."""
    rows = db.execute(
        select(User, UserCompanyRole.role)
        .join(UserCompanyRole, UserCompanyRole.user_id == User.id)
        .where(UserCompanyRole.company_id == current_user.active_company_id)
        .order_by(User.full_name.asc())
    ).all()
    return [CompanyUserOut(id=user.id, full_name=user.full_name, email=user.email, role=role) for user, role in rows]
