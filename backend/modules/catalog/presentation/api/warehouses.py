import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import CreateWarehouseInput, UpdateWarehouseInput
from modules.catalog.application.use_cases import CreateWarehouseUseCase, UpdateWarehouseUseCase
from modules.catalog.infrastructure.repositories.warehouse_repository import WarehouseRepository
from modules.catalog.presentation.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListOut,
    WarehouseOut,
    WarehouseUpdate,
)

router = APIRouter()


@router.get("/warehouses", response_model=WarehouseListOut)
def list_warehouses(
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:warehouses:read")),
) -> WarehouseListOut:
    repo = WarehouseRepository(db)
    items = repo.list(company_id=current_user.active_company_id, include_hidden=include_hidden)
    return WarehouseListOut(items=[WarehouseOut.model_validate(w) for w in items])


@router.post("/warehouses", response_model=WarehouseOut)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:warehouses:write")),
) -> WarehouseOut:
    use_case = CreateWarehouseUseCase(db)
    warehouse = use_case.execute(
        CreateWarehouseInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            address=payload.address,
        )
    )
    db.commit()
    db.refresh(warehouse)
    return WarehouseOut.model_validate(warehouse)


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:warehouses:read")),
) -> WarehouseOut:
    repo = WarehouseRepository(db)
    warehouse = repo.get(company_id=current_user.active_company_id, warehouse_id=warehouse_id)
    if warehouse is None:
        raise NotFoundError("Warehouse not found")
    return WarehouseOut.model_validate(warehouse)


@router.patch("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: uuid.UUID,
    payload: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:warehouses:write")),
) -> WarehouseOut:
    use_case = UpdateWarehouseUseCase(db)
    warehouse = use_case.execute(
        UpdateWarehouseInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            warehouse_id=warehouse_id,
            name=payload.name,
            address=payload.address,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(warehouse)
    return WarehouseOut.model_validate(warehouse)
