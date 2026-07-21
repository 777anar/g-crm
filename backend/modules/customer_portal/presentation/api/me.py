import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.companies.models import Company
from core.db.session import get_db
from core.storage.client import storage_client
from modules.crm.infrastructure.models.customer import Customer
from modules.customer_portal.infrastructure.auth_dependency import CurrentCustomer, get_current_customer
from modules.customer_portal.infrastructure.repositories.portal_query_repository import PortalQueryRepository
from modules.customer_portal.presentation.schemas.portal import (
    PortalDocumentListOut,
    PortalDocumentOut,
    PortalInstallationJobListOut,
    PortalInstallationJobOut,
    PortalInvoiceListOut,
    PortalInvoiceOut,
    PortalMeOut,
    PortalOrderListOut,
    PortalOrderOut,
    PortalQuoteListOut,
    PortalQuoteOut,
    PortalSignedUrlOut,
)
from modules.orders.infrastructure.repositories.order_repository import OrderRepository

router = APIRouter()


@router.get("/me", response_model=PortalMeOut)
def get_me(
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalMeOut:
    customer = db.scalar(
        select(Customer).where(Customer.id == current.customer_id, Customer.company_id == current.company_id)
    )
    if customer is None:
        raise NotFoundError("Customer not found")
    company = db.get(Company, current.company_id)
    return PortalMeOut(
        customer_id=customer.id,
        name=customer.name,
        email=customer.email or "",
        phone=customer.phone,
        company_id=current.company_id,
        company_name=company.name if company else "",
    )


@router.get("/me/orders", response_model=PortalOrderListOut)
def list_my_orders(
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalOrderListOut:
    offset = decode_cursor(cursor)
    items = OrderRepository(db).list(
        company_id=current.company_id, customer_id=current.customer_id, limit=limit + 1, offset=offset
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return PortalOrderListOut(items=[PortalOrderOut.model_validate(o) for o in page], next_cursor=next_cursor)


@router.get("/me/orders/{order_id}", response_model=PortalOrderOut)
def get_my_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalOrderOut:
    order = OrderRepository(db).get(company_id=current.company_id, order_id=order_id)
    if order is None or order.customer_id != current.customer_id:
        raise NotFoundError("Order not found")
    return PortalOrderOut.model_validate(order)


@router.get("/me/quotes", response_model=PortalQuoteListOut)
def list_my_quotes(
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalQuoteListOut:
    offset = decode_cursor(cursor)
    repo = PortalQueryRepository(db)
    items = repo.list_quotes(
        company_id=current.company_id, customer_id=current.customer_id, limit=limit + 1, offset=offset
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return PortalQuoteListOut(items=[PortalQuoteOut.model_validate(q) for q in page], next_cursor=next_cursor)


@router.get("/me/quotes/{quote_id}", response_model=PortalQuoteOut)
def get_my_quote(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalQuoteOut:
    quote = PortalQueryRepository(db).get_quote(
        company_id=current.company_id, customer_id=current.customer_id, quote_id=quote_id
    )
    if quote is None:
        raise NotFoundError("Quote not found")
    return PortalQuoteOut.model_validate(quote)


@router.get("/me/invoices", response_model=PortalInvoiceListOut)
def list_my_invoices(
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalInvoiceListOut:
    offset = decode_cursor(cursor)
    repo = PortalQueryRepository(db)
    items = repo.list_invoices(
        company_id=current.company_id, customer_id=current.customer_id, limit=limit + 1, offset=offset
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return PortalInvoiceListOut(items=[PortalInvoiceOut.model_validate(i) for i in page], next_cursor=next_cursor)


@router.get("/me/invoices/{invoice_id}", response_model=PortalInvoiceOut)
def get_my_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalInvoiceOut:
    invoice = PortalQueryRepository(db).get_invoice(
        company_id=current.company_id, customer_id=current.customer_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise NotFoundError("Invoice not found")
    return PortalInvoiceOut.model_validate(invoice)


@router.get("/me/installation-jobs", response_model=PortalInstallationJobListOut)
def list_my_installation_jobs(
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalInstallationJobListOut:
    offset = decode_cursor(cursor)
    repo = PortalQueryRepository(db)
    items = repo.list_installation_jobs(
        company_id=current.company_id, customer_id=current.customer_id, limit=limit + 1, offset=offset
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return PortalInstallationJobListOut(
        items=[PortalInstallationJobOut.model_validate(j) for j in page], next_cursor=next_cursor
    )


@router.get("/me/installation-jobs/{job_id}", response_model=PortalInstallationJobOut)
def get_my_installation_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalInstallationJobOut:
    job = PortalQueryRepository(db).get_installation_job(
        company_id=current.company_id, customer_id=current.customer_id, job_id=job_id
    )
    if job is None:
        raise NotFoundError("Installation job not found")
    return PortalInstallationJobOut.model_validate(job)


@router.get("/me/documents", response_model=PortalDocumentListOut)
def list_my_documents(
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalDocumentListOut:
    offset = decode_cursor(cursor)
    repo = PortalQueryRepository(db)
    items = repo.list_documents(
        company_id=current.company_id, customer_id=current.customer_id, limit=limit + 1, offset=offset
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return PortalDocumentListOut(items=[PortalDocumentOut.model_validate(d) for d in page], next_cursor=next_cursor)


@router.get("/me/documents/{document_id}/download", response_model=PortalSignedUrlOut)
def download_my_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalSignedUrlOut:
    document = PortalQueryRepository(db).get_document(
        company_id=current.company_id, customer_id=current.customer_id, document_id=document_id
    )
    if document is None:
        raise NotFoundError("Document not found")
    url = storage_client.get_signed_url(key=document.storage_path)
    return PortalSignedUrlOut(url=url)
