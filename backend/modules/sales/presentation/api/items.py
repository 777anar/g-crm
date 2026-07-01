import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateItemInput, UpdateItemInput
from modules.sales.application.use_cases import (
    CreateItemUseCase,
    DeleteItemUseCase,
    UpdateItemUseCase,
)
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.presentation.schemas.item import (
    ItemCreate,
    ItemListOut,
    ItemOut,
    ItemUpdate,
)

router = APIRouter()


@router.get("/sections/{section_id}/items", response_model=ItemListOut)
def list_items(
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:read")),
) -> ItemListOut:
    items = ItemRepository(db).list_for_section(
        company_id=current_user.active_company_id, section_id=section_id
    )
    return ItemListOut(items=[ItemOut.model_validate(i) for i in items])


@router.post("/sections/{section_id}/items", response_model=ItemOut)
def create_item(
    section_id: uuid.UUID,
    payload: ItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> ItemOut:
    uc = CreateItemUseCase(db)
    item = uc.execute(
        CreateItemInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            section_id=section_id,
            item_type=payload.item_type,
            description=payload.description,
            material_id=payload.material_id,
            slab_id=payload.slab_id,
            quantity=payload.quantity,
            unit=payload.unit,
            unit_sale_price=payload.unit_sale_price,
            unit_cost_price=payload.unit_cost_price,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(item)
    return ItemOut.model_validate(item)


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> ItemOut:
    uc = UpdateItemUseCase(db)
    item = uc.execute(
        UpdateItemInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            item_id=item_id,
            description=payload.description,
            material_id=payload.material_id,
            slab_id=payload.slab_id,
            quantity=payload.quantity,
            unit=payload.unit,
            unit_sale_price=payload.unit_sale_price,
            unit_cost_price=payload.unit_cost_price,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(item)
    return ItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> None:
    uc = DeleteItemUseCase(db)
    uc.execute(
        company_id=current_user.active_company_id,
        actor_user_id=current_user.user_id,
        item_id=item_id,
    )
    db.commit()
