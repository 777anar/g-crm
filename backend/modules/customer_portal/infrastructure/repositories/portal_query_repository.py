"""Read-only cross-module queries for the customer-facing portal. Every
method here is hard-scoped by (company_id, customer_id) taken from the
caller's own customer token -- never a client-supplied filter -- so a
customer can only ever see rows that are actually theirs. This mirrors the
same "depends_on for read access" pattern Reports and Marketing already use:
customer_portal's manifest declares depends_on=["crm", "sales", "orders",
"finance", "installation"], and this file is the only place those
dependencies are exercised."""
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.storage.models import Document
from modules.finance.infrastructure.models.invoice import Invoice
from modules.installation.infrastructure.models.installation_job import InstallationJob
from modules.orders.infrastructure.models.order import Order
from modules.sales.infrastructure.models.quote import Quote

# A customer must never see a Quote/Invoice their sales/finance staff hasn't
# finalized yet -- "draft" on either means "not sent, internal working copy."
_CUSTOMER_HIDDEN_STATUS = "draft"

# Every document related_entity_type a customer might legitimately see:
# their own CRM record's attachments, and photos/signatures from their own
# installation jobs. Deliberately excludes internal-only document types
# (e.g. catalog material images, communication message attachments).
_CUSTOMER_VISIBLE_DOCUMENT_TYPES = {"customer", "installation_job"}


class PortalQueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def _order_ids_for_customer(self, *, company_id: uuid.UUID, customer_id: uuid.UUID) -> List[uuid.UUID]:
        return list(
            self.db.scalars(
                select(Order.id).where(Order.company_id == company_id, Order.customer_id == customer_id)
            ).all()
        )

    def list_quotes(
        self, *, company_id: uuid.UUID, customer_id: uuid.UUID, limit: int = 25, offset: int = 0
    ) -> List[Quote]:
        stmt = (
            select(Quote)
            .where(
                Quote.company_id == company_id,
                Quote.customer_id == customer_id,
                Quote.status != _CUSTOMER_HIDDEN_STATUS,
            )
            .order_by(Quote.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_quote(self, *, company_id: uuid.UUID, customer_id: uuid.UUID, quote_id: uuid.UUID) -> Optional[Quote]:
        return self.db.scalar(
            select(Quote).where(
                Quote.id == quote_id,
                Quote.company_id == company_id,
                Quote.customer_id == customer_id,
                Quote.status != _CUSTOMER_HIDDEN_STATUS,
            )
        )

    def list_invoices(
        self, *, company_id: uuid.UUID, customer_id: uuid.UUID, limit: int = 25, offset: int = 0
    ) -> List[Invoice]:
        stmt = (
            select(Invoice)
            .where(
                Invoice.company_id == company_id,
                Invoice.customer_id == customer_id,
                Invoice.status != _CUSTOMER_HIDDEN_STATUS,
            )
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_invoice(self, *, company_id: uuid.UUID, customer_id: uuid.UUID, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return self.db.scalar(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.company_id == company_id,
                Invoice.customer_id == customer_id,
                Invoice.status != _CUSTOMER_HIDDEN_STATUS,
            )
        )

    def list_installation_jobs(
        self, *, company_id: uuid.UUID, customer_id: uuid.UUID, limit: int = 25, offset: int = 0
    ) -> List[InstallationJob]:
        order_ids = self._order_ids_for_customer(company_id=company_id, customer_id=customer_id)
        if not order_ids:
            return []
        stmt = (
            select(InstallationJob)
            .where(InstallationJob.company_id == company_id, InstallationJob.order_id.in_(order_ids))
            .order_by(InstallationJob.scheduled_date.desc().nulls_last(), InstallationJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_installation_job(
        self, *, company_id: uuid.UUID, customer_id: uuid.UUID, job_id: uuid.UUID
    ) -> Optional[InstallationJob]:
        order_ids = self._order_ids_for_customer(company_id=company_id, customer_id=customer_id)
        if not order_ids:
            return None
        return self.db.scalar(
            select(InstallationJob).where(
                InstallationJob.id == job_id,
                InstallationJob.company_id == company_id,
                InstallationJob.order_id.in_(order_ids),
            )
        )

    def list_documents(
        self, *, company_id: uuid.UUID, customer_id: uuid.UUID, limit: int = 25, offset: int = 0
    ) -> List[Document]:
        order_ids = self._order_ids_for_customer(company_id=company_id, customer_id=customer_id)
        job_ids: List[uuid.UUID] = []
        if order_ids:
            job_ids = list(
                self.db.scalars(
                    select(InstallationJob.id).where(
                        InstallationJob.company_id == company_id, InstallationJob.order_id.in_(order_ids)
                    )
                ).all()
            )
        conditions = [
            (Document.related_entity_type == "customer") & (Document.related_entity_id == customer_id)
        ]
        if job_ids:
            conditions.append(
                (Document.related_entity_type == "installation_job") & (Document.related_entity_id.in_(job_ids))
            )
        stmt = (
            select(Document)
            .where(Document.company_id == company_id, or_(*conditions))
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_document(self, *, company_id: uuid.UUID, customer_id: uuid.UUID, document_id: uuid.UUID) -> Optional[Document]:
        document = self.db.get(Document, document_id)
        if document is None or document.company_id != company_id:
            return None
        if document.related_entity_type not in _CUSTOMER_VISIBLE_DOCUMENT_TYPES:
            return None
        if document.related_entity_type == "customer":
            if document.related_entity_id != customer_id:
                return None
            return document
        # installation_job
        order_ids = self._order_ids_for_customer(company_id=company_id, customer_id=customer_id)
        if not order_ids:
            return None
        job = self.db.scalar(
            select(InstallationJob).where(
                InstallationJob.id == document.related_entity_id,
                InstallationJob.company_id == company_id,
                InstallationJob.order_id.in_(order_ids),
            )
        )
        return document if job is not None else None
