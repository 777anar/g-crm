from fastapi import APIRouter

from modules.finance.presentation.api.expenses import router as expenses_router
from modules.finance.presentation.api.export import router as export_router
from modules.finance.presentation.api.invoices import router as invoices_router
from modules.finance.presentation.api.payments_webhook import router as payments_webhook_router

finance_router_main = APIRouter()
finance_router_main.include_router(invoices_router)
finance_router_main.include_router(expenses_router)
finance_router_main.include_router(export_router)
finance_router_main.include_router(payments_webhook_router)
