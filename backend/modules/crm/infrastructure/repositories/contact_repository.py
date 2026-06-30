import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.crm.infrastructure.models.contact import Contact


class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, contact: Contact) -> Contact:
        self.db.add(contact)
        self.db.flush()
        return contact

    def get(self, *, company_id: uuid.UUID, contact_id: uuid.UUID) -> Optional[Contact]:
        return self.db.scalar(
            select(Contact).where(Contact.id == contact_id, Contact.company_id == company_id)
        )

    def list_for_customer(self, *, company_id: uuid.UUID, customer_id: uuid.UUID) -> List[Contact]:
        stmt = select(Contact).where(Contact.company_id == company_id, Contact.customer_id == customer_id)
        return list(self.db.scalars(stmt).all())
