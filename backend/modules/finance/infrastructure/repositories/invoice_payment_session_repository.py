import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.finance.infrastructure.models.invoice_payment_session import InvoicePaymentSession


class InvoicePaymentSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, session: InvoicePaymentSession) -> InvoicePaymentSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get(self, *, company_id: uuid.UUID, session_id: uuid.UUID) -> Optional[InvoicePaymentSession]:
        return self.db.scalar(
            select(InvoicePaymentSession).where(
                InvoicePaymentSession.id == session_id, InvoicePaymentSession.company_id == company_id
            )
        )

    def get_by_provider_session_id(self, *, provider: str, provider_session_id: str) -> Optional[InvoicePaymentSession]:
        return self.db.scalar(
            select(InvoicePaymentSession).where(
                InvoicePaymentSession.provider == provider,
                InvoicePaymentSession.provider_session_id == provider_session_id,
            )
        )
