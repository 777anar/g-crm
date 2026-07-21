import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.purchasing.application.dtos import CreateSupplierInput, UpdateSupplierInput
from modules.purchasing.application.use_cases import CreateSupplierUseCase, UpdateSupplierUseCase
from modules.purchasing.infrastructure.repositories.supplier_repository import SupplierRepository
from modules.purchasing.presentation.schemas.supplier import (
    SupplierCreate,
    SupplierListOut,
    SupplierOut,
    SupplierUpdate,
)

router = APIRouter()


@router.get("/suppliers", response_model=SupplierListOut)
def list_suppliers(
    include_hidden: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:suppliers:read")),
) -> SupplierListOut:
    repo = SupplierRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        include_hidden=include_hidden,
        search=search,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return SupplierListOut(items=[SupplierOut.model_validate(s) for s in page], next_cursor=next_cursor)


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:suppliers:write")),
) -> SupplierOut:
    supplier = CreateSupplierUseCase(db).execute(
        CreateSupplierInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            contact_name=payload.contact_name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:suppliers:read")),
) -> SupplierOut:
    supplier = SupplierRepository(db).get(company_id=current_user.active_company_id, supplier_id=supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier not found")
    return SupplierOut.model_validate(supplier)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:suppliers:write")),
) -> SupplierOut:
    supplier = UpdateSupplierUseCase(db).execute(
        UpdateSupplierInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            supplier_id=supplier_id,
            name=payload.name,
            contact_name=payload.contact_name,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            notes=payload.notes,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)
