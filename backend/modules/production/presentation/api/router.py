from fastapi import APIRouter

from modules.production.presentation.api.work_orders import router as work_orders_router

production_router_main = work_orders_router
