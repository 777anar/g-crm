import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.finance.infrastructure.models.invoice_line import InvoiceLine


class InvoiceLineRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, line: InvoiceLine) -> InvoiceLine:
        self.db.add(line)
        self.db.flush()
        return line

    def list_for_invoice(self, *, company_id: uuid.UUID, invoice_id: uuid.UUID) -> List[InvoiceLine]:
        stmt = (
            select(InvoiceLine)
            .where(InvoiceLine.company_id == company_id, InvoiceLine.invoice_id == invoice_id)
            .order_by(InvoiceLine.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())
