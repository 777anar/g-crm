import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.finance.domain.value_objects import VALID_EXPENSE_CATEGORIES, VALID_INVOICE_STATUSES, VALID_PAYMENT_METHODS


class InvoiceCreate(BaseModel):
    order_id: uuid.UUID
    due_date: Optional[str] = None
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    due_date: Optional[str] = None
    notes: Optional[str] = None


class InvoiceStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None

    def model_post_init(self, __context):
        if self.status not in VALID_INVOICE_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class InvoiceOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    customer_id: uuid.UUID
    installation_job_id: Optional[uuid.UUID]
    invoice_number: str
    status: str
    currency: str
    subtotal_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    issue_date: str
    due_date: Optional[str]
    notes: Optional[str]
    sent_at: Optional[datetime]
    paid_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListOut(BaseModel):
    items: List[InvoiceOut]
    next_cursor: Optional[str] = None


class InvoiceLineOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    invoice_id: uuid.UUID
    description: str
    amount: Decimal
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceLineListOut(BaseModel):
    items: List[InvoiceLineOut]


class PaymentCreate(BaseModel):
    amount: Decimal
    method: str = "cash"
    paid_at: Optional[datetime] = None
    reference_note: Optional[str] = None

    def model_post_init(self, __context):
        if self.method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method: {self.method}")


class PaymentOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: str
    paid_at: datetime
    reference_note: Optional[str]
    recorded_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListOut(BaseModel):
    items: List[PaymentOut]


class ExpenseCreate(BaseModel):
    category: str = "other"
    amount: Decimal
    expense_date: str
    order_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    currency: str = "AZN"

    def model_post_init(self, __context):
        if self.category not in VALID_EXPENSE_CATEGORIES:
            raise ValueError(f"Invalid expense category: {self.category}")


class ExpenseOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: Optional[uuid.UUID]
    category: str
    description: Optional[str]
    amount: Decimal
    currency: str
    expense_date: str
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseListOut(BaseModel):
    items: List[ExpenseOut]
    next_cursor: Optional[str] = None
