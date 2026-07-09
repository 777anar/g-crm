import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateRoomInput, UpdateRoomInput
from modules.sales.application.use_cases import CreateRoomUseCase, DeleteRoomUseCase, UpdateRoomUseCase
from modules.sales.infrastructure.repositories.room_repository import RoomRepository
from modules.sales.presentation.schemas.room import RoomCreate, RoomListOut, RoomOut, RoomUpdate

router = APIRouter()


@router.get("/projects/{project_id}/rooms", response_model=RoomListOut)
def list_rooms(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> RoomListOut:
    items = RoomRepository(db).list_for_project(company_id=current_user.active_company_id, project_id=project_id)
    return RoomListOut(items=[RoomOut.model_validate(r) for r in items])


@router.post("/projects/{project_id}/rooms", response_model=RoomOut)
def create_room(
    project_id: uuid.UUID,
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> RoomOut:
    uc = CreateRoomUseCase(db)
    room = uc.execute(
        CreateRoomInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_id=project_id,
            room_type=payload.room_type,
            name=payload.name,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(room)
    return RoomOut.model_validate(room)


@router.patch("/rooms/{room_id}", response_model=RoomOut)
def update_room(
    room_id: uuid.UUID,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> RoomOut:
    uc = UpdateRoomUseCase(db)
    room = uc.execute(
        UpdateRoomInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            room_id=room_id,
            room_type=payload.room_type,
            name=payload.name,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(room)
    return RoomOut.model_validate(room)


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(
    room_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> None:
    uc = DeleteRoomUseCase(db)
    uc.execute(company_id=current_user.active_company_id, actor_user_id=current_user.user_id, room_id=room_id)
    db.commit()
