import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.crm.domain.entities import Customer as CustomerEntity
from modules.crm.infrastructure.models.customer import Customer as CustomerModel


def _to_entity(model: CustomerModel) -> CustomerEntity:
    return CustomerEntity(
        id=model.id,
        company_id=model.company_id,
        name=model.name,
        type=model.type,
        primary_contact_id=model.primary_contact_id,
        assigned_manager_id=model.assigned_manager_id,
        lead_source=model.lead_source,
        advertising_campaign=model.advertising_campaign,
        phone=model.phone,
        whatsapp=model.whatsapp,
        instagram=model.instagram,
        facebook=model.facebook,
        email=model.email,
        address=model.address,
        company_name=model.company_name,
        notes=model.notes,
        status=model.status,
        tags=list(model.tags or []),
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, model: CustomerModel) -> CustomerModel:
        self.db.add(model)
        self.db.flush()
        return model

    def get_model(self, *, company_id: uuid.UUID, customer_id: uuid.UUID) -> Optional[CustomerModel]:
        return self.db.scalar(
            select(CustomerModel).where(
                CustomerModel.id == customer_id, CustomerModel.company_id == company_id
            )
        )

    def get(self, *, company_id: uuid.UUID, customer_id: uuid.UUID) -> Optional[CustomerEntity]:
        model = self.get_model(company_id=company_id, customer_id=customer_id)
        return _to_entity(model) if model else None

    def list(
        self,
        *,
        company_id: uuid.UUID,
        include_archived: bool = False,
        assigned_manager_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        lead_source: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[CustomerEntity]:
        stmt = select(CustomerModel).where(CustomerModel.company_id == company_id)
        if not include_archived:
            stmt = stmt.where(CustomerModel.deleted_at.is_(None))
        if assigned_manager_id:
            stmt = stmt.where(CustomerModel.assigned_manager_id == assigned_manager_id)
        if status:
            stmt = stmt.where(CustomerModel.status == status)
        if lead_source:
            stmt = stmt.where(CustomerModel.lead_source == lead_source)
        stmt = stmt.order_by(CustomerModel.created_at.desc()).offset(offset).limit(limit)
        return [_to_entity(m) for m in self.db.scalars(stmt).all()]
