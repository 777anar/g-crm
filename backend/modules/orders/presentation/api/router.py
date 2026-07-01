from fastapi import APIRouter

from modules.orders.presentation.api.orders import router as orders_router

orders_router_main = orders_router
