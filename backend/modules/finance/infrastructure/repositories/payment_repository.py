import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.finance.infrastructure.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def list_for_invoice(self, *, company_id: uuid.UUID, invoice_id: uuid.UUID) -> List[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.company_id == company_id, Payment.invoice_id == invoice_id)
            .order_by(Payment.paid_at.desc())
        )
        return list(self.db.scalars(stmt).all())
