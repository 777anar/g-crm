from fastapi import APIRouter

from modules.finance.presentation.api.expenses import router as expenses_router
from modules.finance.presentation.api.invoices import router as invoices_router

finance_router_main = APIRouter()
finance_router_main.include_router(invoices_router)
finance_router_main.include_router(expenses_router)
