import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.project import Project

_SORTABLE = {
    "name": Project.name,
    "created_at": Project.created_at,
    "status": Project.status,
}


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, project: Project) -> Project:
        self.db.add(project)
        self.db.flush()
        return project

    def get(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Optional[Project]:
        return self.db.scalar(
            select(Project).where(Project.id == project_id, Project.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Project]:
        stmt = select(Project).where(Project.company_id == company_id)
        if customer_id:
            stmt = stmt.where(Project.customer_id == customer_id)
        if status:
            stmt = stmt.where(Project.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(Project.name.ilike(pattern))

        sort_col = _SORTABLE.get((sort or "-created_at").lstrip("-"), Project.created_at)
        desc = not sort or sort.startswith("-")
        stmt = stmt.order_by(sort_col.desc() if desc else sort_col.asc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
