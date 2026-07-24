from fastapi import APIRouter

from modules.purchasing.presentation.api.purchase_orders import router as purchase_orders_router
from modules.purchasing.presentation.api.suppliers import router as suppliers_router
from modules.purchasing.presentation.api.procurement import router as procurement_router

purchasing_router_main = APIRouter()
purchasing_router_main.include_router(suppliers_router)
purchasing_router_main.include_router(purchase_orders_router)
purchasing_router_main.include_router(procurement_router)
