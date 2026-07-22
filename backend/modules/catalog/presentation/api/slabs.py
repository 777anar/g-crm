import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, ConflictError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import (
    CreateOffcutInput,
    CreateSlabInput,
    CreateSlabReservationInput,
    ReleaseSlabReservationInput,
    UpdateSlabStatusInput,
)
from modules.catalog.application.use_cases import (
    CreateOffcutUseCase,
    CreateSlabReservationUseCase,
    CreateSlabUseCase,
    ReleaseSlabReservationUseCase,
    UpdateSlabStatusUseCase,
)
from modules.catalog.domain.exceptions import (
    DuplicateSlabNumberError,
    InvalidSlabTransitionError,
    SlabAlreadyReservedError,
    SlabNotInProductionError,
    SlabNotReservableError,
)
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.catalog.infrastructure.repositories.slab_reservation_repository import SlabReservationRepository
from modules.catalog.presentation.schemas.slab import (
    OffcutCreate,
    OffcutListOut,
    SlabCreate,
    SlabListOut,
    SlabOut,
    SlabReservationCreate,
    SlabReservationListOut,
    SlabReservationOut,
    SlabStatusUpdate,
)

router = APIRouter()

_RESERVATION_BUSINESS_ERRORS = (SlabAlreadyReservedError, SlabNotReservableError, SlabNotInProductionError)


@router.get("/slabs", response_model=SlabListOut)
def list_slabs(
    material_id: Optional[uuid.UUID] = Query(default=None),
    warehouse_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Matches slab number, lot number, or barcode"),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:read")),
) -> SlabListOut:
    repo = SlabRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        material_id=material_id,
        warehouse_id=warehouse_id,
        status=status,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return SlabListOut(items=[SlabOut.model_validate(s) for s in page], next_cursor=next_cursor)


@router.get("/slabs/offcuts", response_model=OffcutListOut)
def search_offcuts(
    material_id: Optional[uuid.UUID] = Query(default=None),
    thickness_mm: Optional[str] = Query(default=None),
    finish: Optional[str] = Query(default=None),
    warehouse_id: Optional[uuid.UUID] = Query(default=None),
    min_length_mm: Optional[str] = Query(default=None),
    min_width_mm: Optional[str] = Query(default=None),
    min_area_m2: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Matches slab number"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:read")),
) -> OffcutListOut:
    """The Offcut Library search (Phase 2 requirement #3) -- always
    `is_offcut=true` and `status=available`, filterable by material,
    thickness, finish, warehouse, minimum usable dimensions, and minimum
    available area. Registered ahead of `GET /slabs/{slab_id}` below so
    the literal `offcuts` path segment is never swallowed by that
    catch-all id route."""
    repo = SlabRepository(db)
    items = repo.search_offcuts(
        company_id=current_user.active_company_id,
        material_id=material_id,
        thickness_mm=thickness_mm,
        finish=finish,
        warehouse_id=warehouse_id,
        min_length_mm=Decimal(min_length_mm) if min_length_mm else None,
        min_width_mm=Decimal(min_width_mm) if min_width_mm else None,
        min_area_m2=Decimal(min_area_m2) if min_area_m2 else None,
        search=search,
        limit=limit,
    )
    return OffcutListOut(items=[SlabOut.model_validate(s) for s in items])


@router.post("/slabs", response_model=SlabOut)
def create_slab(
    payload: SlabCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:write")),
) -> SlabOut:
    use_case = CreateSlabUseCase(db)
    try:
        slab = use_case.execute(
            CreateSlabInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                material_id=payload.material_id,
                warehouse_id=payload.warehouse_id,
                slab_number=payload.slab_number,
                lot_number=payload.lot_number,
                barcode=payload.barcode,
                rack_location=payload.rack_location,
                length_mm=payload.length_mm,
                width_mm=payload.width_mm,
                weight_kg=payload.weight_kg,
                status=payload.status,
            )
        )
    except DuplicateSlabNumberError as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    db.refresh(slab)
    return SlabOut.model_validate(slab)


@router.get("/slabs/{slab_id}", response_model=SlabOut)
def get_slab(
    slab_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:read")),
) -> SlabOut:
    repo = SlabRepository(db)
    slab = repo.get(company_id=current_user.active_company_id, slab_id=slab_id)
    if slab is None:
        raise NotFoundError("Slab not found")
    return SlabOut.model_validate(slab)


@router.patch("/slabs/{slab_id}/status", response_model=SlabOut)
def update_slab_status(
    slab_id: uuid.UUID,
    payload: SlabStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:write")),
) -> SlabOut:
    use_case = UpdateSlabStatusUseCase(db)
    try:
        slab = use_case.execute(
            UpdateSlabStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                slab_id=slab_id,
                status=payload.status,
            )
        )
    except InvalidSlabTransitionError as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    db.refresh(slab)
    return SlabOut.model_validate(slab)


@router.get("/slabs/{slab_id}/reservations", response_model=SlabReservationListOut)
def list_slab_reservations(
    slab_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:read")),
) -> SlabReservationListOut:
    rows = SlabReservationRepository(db).list_for_slab(company_id=current_user.active_company_id, slab_id=slab_id)
    return SlabReservationListOut(items=[SlabReservationOut.model_validate(r) for r in rows])


@router.post("/slabs/{slab_id}/reserve", response_model=SlabReservationOut)
def reserve_slab(
    slab_id: uuid.UUID,
    payload: SlabReservationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:write")),
) -> SlabReservationOut:
    use_case = CreateSlabReservationUseCase(db)
    try:
        reservation = use_case.execute(
            CreateSlabReservationInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                slab_id=slab_id,
                order_id=payload.order_id,
                order_item_id=payload.order_item_id,
                notes=payload.notes,
            )
        )
    except _RESERVATION_BUSINESS_ERRORS as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    db.refresh(reservation)
    return SlabReservationOut.model_validate(reservation)


@router.post("/slabs/reservations/{reservation_id}/release", response_model=SlabReservationOut)
def release_slab_reservation(
    reservation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:write")),
) -> SlabReservationOut:
    use_case = ReleaseSlabReservationUseCase(db)
    reservation = use_case.execute(
        ReleaseSlabReservationInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            reservation_id=reservation_id,
        )
    )
    db.commit()
    db.refresh(reservation)
    return SlabReservationOut.model_validate(reservation)


@router.get("/reservations", response_model=SlabReservationListOut)
def list_reservations_for_order(
    order_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:read")),
) -> SlabReservationListOut:
    rows = SlabReservationRepository(db).list_for_order(company_id=current_user.active_company_id, order_id=order_id)
    return SlabReservationListOut(items=[SlabReservationOut.model_validate(r) for r in rows])


@router.post("/slabs/{slab_id}/offcuts", response_model=SlabOut)
def create_offcut(
    slab_id: uuid.UUID,
    payload: OffcutCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:slabs:write")),
) -> SlabOut:
    use_case = CreateOffcutUseCase(db)
    try:
        offcut = use_case.execute(
            CreateOffcutInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                parent_slab_id=slab_id,
                warehouse_id=payload.warehouse_id,
                slab_number=payload.slab_number,
                length_mm=payload.length_mm,
                width_mm=payload.width_mm,
                weight_kg=payload.weight_kg,
                notes=payload.notes,
            )
        )
    except DuplicateSlabNumberError as exc:
        raise ConflictError(str(exc)) from exc
    except _RESERVATION_BUSINESS_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(offcut)
    return SlabOut.model_validate(offcut)
