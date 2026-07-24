"""Application-layer input DTOs for the Finance module."""
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateInvoiceInput(ActorContext):
    order_id: uuid.UUID
    due_date: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UpdateInvoiceInput(ActorContext):
    invoice_id: uuid.UUID
    due_date: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UpdateInvoiceStatusInput(ActorContext):
    invoice_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None


@dataclass
class RecordPaymentInput(ActorContext):
    invoice_id: uuid.UUID
    amount: Decimal
    method: str
    paid_at: Optional[datetime] = None
    reference_note: Optional[str] = None


@dataclass
class CreateExpenseInput(ActorContext):
    category: str
    amount: Decimal
    expense_date: str
    order_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    currency: str = "AZN"


# ── Payment sessions (Phase 22) -- customer-initiated, no staff actor ───────


@dataclass
class CreatePaymentSessionInput:
    company_id: uuid.UUID
    customer_id: uuid.UUID
    invoice_id: uuid.UUID
    success_url: str
    cancel_url: str
    provider_name: Optional[str] = None


@dataclass
class SimulatePaymentSessionInput:
    company_id: uuid.UUID
    customer_id: uuid.UUID
    session_id: uuid.UUID
    outcome: str  # "completed" | "failed"


@dataclass
class HandlePaymentWebhookInput:
    raw_body: bytes
    signature_header: str
    provider_name: str
