import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.finance.infrastructure.models.invoice import Invoice
from modules.finance.infrastructure.models.invoice_number_sequence import InvoiceNumberSequence


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def get(self, *, company_id: uuid.UUID, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return self.db.scalar(
            select(Invoice).where(Invoice.id == invoice_id, Invoice.company_id == company_id)
        )

    def get_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> Optional[Invoice]:
        return self.db.scalar(
            select(Invoice).where(Invoice.order_id == order_id, Invoice.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Invoice]:
        stmt = select(Invoice).where(Invoice.company_id == company_id)
        if customer_id:
            stmt = stmt.where(Invoice.customer_id == customer_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
        if search:
            stmt = stmt.where(Invoice.invoice_number.ilike(f"%{search}%"))
        stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def next_invoice_number(self, *, company_id: uuid.UUID, year: int) -> str:
        """Atomically increments the per-company-per-year counter and returns
        a formatted invoice number like 'INV-2026-0001'."""
        seq = self.db.scalar(
            select(InvoiceNumberSequence).where(
                InvoiceNumberSequence.company_id == company_id,
                InvoiceNumberSequence.year == year,
            )
        )
        if seq is None:
            seq = InvoiceNumberSequence(company_id=company_id, year=year, last_number=0)
            self.db.add(seq)
            self.db.flush()
        seq.last_number += 1
        self.db.flush()
        return f"INV-{year}-{seq.last_number:04d}"
