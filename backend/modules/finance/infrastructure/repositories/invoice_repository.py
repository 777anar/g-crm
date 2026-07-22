import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.finance.infrastructure.models.invoice import Invoice
from modules.finance.infrastructure.models.invoice_number_sequence import InvoiceNumberSequence

# Whitelisted sortable columns per the `?sort=field` / `?sort=-field`
# convention every other list endpoint follows (see OrderRepository.list) --
# whitelisting prevents sorting on an arbitrary/unindexed/sensitive column.
_SORTABLE = {
    "invoice_number": Invoice.invoice_number,
    "status": Invoice.status,
    "created_at": Invoice.created_at,
    "due_date": Invoice.due_date,
    "total_amount": Invoice.total_amount,
}


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
        sort: Optional[str] = None,
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
        sort_col = _SORTABLE.get((sort or "-created_at").lstrip("-"), Invoice.created_at)
        desc = not sort or sort.startswith("-")
        stmt = stmt.order_by(sort_col.desc() if desc else sort_col.asc()).offset(offset).limit(limit)
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
