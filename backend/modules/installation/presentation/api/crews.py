import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.auth.models import User
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.installation.application.dtos import (
    AddCrewMemberInput,
    CreateCrewInput,
    RemoveCrewMemberInput,
    UpdateCrewInput,
)
from modules.installation.application.use_cases import (
    AddCrewMemberUseCase,
    CreateCrewUseCase,
    RemoveCrewMemberUseCase,
    UpdateCrewUseCase,
)
from modules.installation.infrastructure.repositories.crew_repository import (
    CrewMemberRepository,
    CrewRepository,
)
from modules.installation.presentation.schemas.crew import (
    CrewCreate,
    CrewListOut,
    CrewMemberCreate,
    CrewMemberListOut,
    CrewMemberOut,
    CrewOut,
    CrewUpdate,
)

router = APIRouter()


@router.get("", response_model=CrewListOut)
def list_crews(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> CrewListOut:
    crews = CrewRepository(db).list(company_id=current_user.active_company_id, status=status)
    return CrewListOut(items=[CrewOut.model_validate(c) for c in crews])


@router.post("", response_model=CrewOut)
def create_crew(
    payload: CrewCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> CrewOut:
    crew = CreateCrewUseCase(db).execute(
        CreateCrewInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(crew)
    return CrewOut.model_validate(crew)


@router.get("/{crew_id}", response_model=CrewOut)
def get_crew(
    crew_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> CrewOut:
    crew = CrewRepository(db).get(company_id=current_user.active_company_id, crew_id=crew_id)
    if crew is None:
        raise NotFoundError("Crew not found")
    return CrewOut.model_validate(crew)


@router.patch("/{crew_id}", response_model=CrewOut)
def update_crew(
    crew_id: uuid.UUID,
    payload: CrewUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> CrewOut:
    crew = UpdateCrewUseCase(db).execute(
        UpdateCrewInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            crew_id=crew_id,
            name=payload.name,
            status=payload.status,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(crew)
    return CrewOut.model_validate(crew)


@router.get("/{crew_id}/members", response_model=CrewMemberListOut)
def list_crew_members(
    crew_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:read")),
) -> CrewMemberListOut:
    rows = CrewMemberRepository(db).list_with_users_for_crew(
        company_id=current_user.active_company_id, crew_id=crew_id
    )
    return CrewMemberListOut(
        items=[
            CrewMemberOut(
                id=member.id,
                crew_id=member.crew_id,
                user_id=member.user_id,
                is_lead=member.is_lead,
                full_name=user.full_name,
                email=user.email,
            )
            for member, user in rows
        ]
    )


@router.post("/{crew_id}/members", response_model=CrewMemberOut)
def add_crew_member(
    crew_id: uuid.UUID,
    payload: CrewMemberCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> CrewMemberOut:
    member = AddCrewMemberUseCase(db).execute(
        AddCrewMemberInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            crew_id=crew_id,
            user_id=payload.user_id,
            is_lead=payload.is_lead,
        )
    )
    db.commit()
    user = db.get(User, payload.user_id)
    return CrewMemberOut(
        id=member.id,
        crew_id=member.crew_id,
        user_id=member.user_id,
        is_lead=member.is_lead,
        full_name=user.full_name if user else "",
        email=user.email if user else "",
    )


@router.delete("/{crew_id}/members/{member_id}", status_code=204)
def remove_crew_member(
    crew_id: uuid.UUID,
    member_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("installation:write")),
) -> None:
    RemoveCrewMemberUseCase(db).execute(
        RemoveCrewMemberInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            crew_id=crew_id,
            member_id=member_id,
        )
    )
    db.commit()
