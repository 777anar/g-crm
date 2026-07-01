import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateSectionInput, UpdateSectionInput
from modules.sales.application.use_cases import (
    CreateSectionUseCase,
    DeleteSectionUseCase,
    UpdateSectionUseCase,
)
from modules.sales.infrastructure.repositories.section_repository import SectionRepository
from modules.sales.presentation.schemas.section import (
    SectionCreate,
    SectionListOut,
    SectionOut,
    SectionUpdate,
)

router = APIRouter()


@router.get("/quotes/{quote_id}/sections", response_model=SectionListOut)
def list_sections(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:read")),
) -> SectionListOut:
    items = SectionRepository(db).list_for_quote(
        company_id=current_user.active_company_id, quote_id=quote_id
    )
    return SectionListOut(items=[SectionOut.model_validate(s) for s in items])


@router.post("/quotes/{quote_id}/sections", response_model=SectionOut)
def create_section(
    quote_id: uuid.UUID,
    payload: SectionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> SectionOut:
    uc = CreateSectionUseCase(db)
    section = uc.execute(
        CreateSectionInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            quote_id=quote_id,
            name=payload.name,
            sort_order=payload.sort_order,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(section)
    return SectionOut.model_validate(section)


@router.patch("/sections/{section_id}", response_model=SectionOut)
def update_section(
    section_id: uuid.UUID,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> SectionOut:
    uc = UpdateSectionUseCase(db)
    section = uc.execute(
        UpdateSectionInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            section_id=section_id,
            name=payload.name,
            sort_order=payload.sort_order,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(section)
    return SectionOut.model_validate(section)


@router.delete("/sections/{section_id}", status_code=204)
def delete_section(
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> None:
    uc = DeleteSectionUseCase(db)
    uc.execute(
        company_id=current_user.active_company_id,
        actor_user_id=current_user.user_id,
        section_id=section_id,
    )
    db.commit()
