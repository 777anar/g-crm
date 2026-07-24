"""Accounting/ERP export (Phase 22): a real, structured export of Finance
data for whatever accounting system (1C and similar are the norm for the
three companies this platform serves) a company reconciles against, closing
the gap between "the data lives in Finance" and "the data leaves Finance
without manual re-entry." Deliberately CSV, not a live bidirectional API --
no specific accounting system's API was named, and CSV import is the one
format every such system accepts, matching this codebase's own established
export convention (Purchasing's `GET /export/{resource}`, Reports' PDF/Excel
exports) rather than inventing a new export mechanism.

Three raw resource exports (for reconciliation-by-hand or a system's own CSV
importer) plus one synthesized double-entry-style journal export -- the
genuinely "accounting" deliverable, mapping this module's own data onto
debit/credit journal lines any bookkeeping system understands.
"""
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.finance.domain.value_objects import PAYMENT_METHOD_CASH
from modules.finance.infrastructure.models.expense import Expense
from modules.finance.infrastructure.models.invoice import Invoice
from modules.finance.infrastructure.models.payment import Payment

router = APIRouter()

_CASH_LIKE_METHODS = {PAYMENT_METHOD_CASH, "card"}


def _csv_response(rows: list, header: list, filename: str) -> Response:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows(rows)
    # UTF-8 BOM so Excel (the most common consumer of an accounting CSV
    # import) renders non-ASCII text correctly instead of mojibake.
    return Response(
        content=("﻿" + out.getvalue()).encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


def _in_range(stmt, column, date_from: Optional[str], date_to: Optional[str]):
    if date_from:
        stmt = stmt.where(column >= date_from)
    if date_to:
        stmt = stmt.where(column <= date_to)
    return stmt


@router.get("/export/{resource}")
def export_finance_data(
    resource: str,
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:export:read")),
) -> Response:
    company_id = current_user.active_company_id

    if resource == "invoices":
        stmt = _in_range(select(Invoice).where(Invoice.company_id == company_id), Invoice.issue_date, date_from, date_to)
        invoices = db.scalars(stmt.order_by(Invoice.issue_date)).all()
        rows = [
            [i.invoice_number, i.issue_date, i.due_date, i.status, i.currency, i.subtotal_amount, i.total_amount, i.amount_paid]
            for i in invoices
        ]
        return _csv_response(
            rows,
            ["invoice_number", "issue_date", "due_date", "status", "currency", "subtotal_amount", "total_amount", "amount_paid"],
            "invoices",
        )

    if resource == "payments":
        stmt = (
            select(Payment, Invoice.invoice_number)
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(Payment.company_id == company_id)
        )
        stmt = _in_range(stmt, Payment.paid_at, date_from, date_to)
        rows = [
            [invoice_number, p.paid_at.date().isoformat() if p.paid_at else "", p.method, p.amount, p.reference_note or ""]
            for p, invoice_number in db.execute(stmt.order_by(Payment.paid_at)).all()
        ]
        return _csv_response(rows, ["invoice_number", "paid_at", "method", "amount", "reference_note"], "payments")

    if resource == "expenses":
        stmt = _in_range(select(Expense).where(Expense.company_id == company_id), Expense.expense_date, date_from, date_to)
        expenses = db.scalars(stmt.order_by(Expense.expense_date)).all()
        rows = [[e.expense_date, e.category, e.currency, e.amount, e.description or ""] for e in expenses]
        return _csv_response(rows, ["expense_date", "category", "currency", "amount", "description"], "expenses")

    if resource == "journal":
        return _journal_export(db, company_id, date_from, date_to)

    raise NotFoundError(f"Unknown export resource '{resource}'")


def _journal_export(db: Session, company_id, date_from: Optional[str], date_to: Optional[str]) -> Response:
    rows = []

    invoices = db.scalars(
        _in_range(select(Invoice).where(Invoice.company_id == company_id), Invoice.issue_date, date_from, date_to).order_by(
            Invoice.issue_date
        )
    ).all()
    for i in invoices:
        rows.append([i.issue_date, "Accounts Receivable", i.total_amount, "", i.invoice_number, f"Invoice {i.invoice_number} issued"])
        rows.append([i.issue_date, "Sales Revenue", "", i.total_amount, i.invoice_number, f"Invoice {i.invoice_number} issued"])

    payment_stmt = (
        select(Payment, Invoice.invoice_number)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(Payment.company_id == company_id)
    )
    for p, invoice_number in db.execute(
        _in_range(payment_stmt, Payment.paid_at, date_from, date_to).order_by(Payment.paid_at)
    ).all():
        paid_date = p.paid_at.date().isoformat() if p.paid_at else ""
        cash_account = "Cash" if p.method in _CASH_LIKE_METHODS else "Bank"
        rows.append([paid_date, cash_account, p.amount, "", invoice_number, f"Payment received for {invoice_number} ({p.method})"])
        rows.append([paid_date, "Accounts Receivable", "", p.amount, invoice_number, f"Payment received for {invoice_number} ({p.method})"])

    expenses = db.scalars(
        _in_range(select(Expense).where(Expense.company_id == company_id), Expense.expense_date, date_from, date_to).order_by(
            Expense.expense_date
        )
    ).all()
    for e in expenses:
        expense_account = f"Expense:{e.category}"
        rows.append([e.expense_date, expense_account, e.amount, "", "", e.description or e.category])
        rows.append([e.expense_date, "Cash", "", e.amount, "", e.description or e.category])

    rows.sort(key=lambda r: r[0] or "")
    return _csv_response(rows, ["date", "account", "debit", "credit", "reference", "memo"], "journal")
