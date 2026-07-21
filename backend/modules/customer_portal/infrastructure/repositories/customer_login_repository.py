import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.customer_portal.infrastructure.models.customer_login import CustomerLogin


class CustomerLoginRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, login: CustomerLogin) -> CustomerLogin:
        self.db.add(login)
        self.db.flush()
        return login

    def get_by_customer(self, *, company_id: uuid.UUID, customer_id: uuid.UUID) -> Optional[CustomerLogin]:
        return self.db.scalar(
            select(CustomerLogin).where(
                CustomerLogin.customer_id == customer_id, CustomerLogin.company_id == company_id
            )
        )

    def get_by_email(self, *, email: str) -> Optional[CustomerLogin]:
        return self.db.scalar(select(CustomerLogin).where(CustomerLogin.email == email))
