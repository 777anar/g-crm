from fastapi import APIRouter

from modules.customer_portal.presentation.api.admin import router as admin_router
from modules.customer_portal.presentation.api.auth import router as auth_router
from modules.customer_portal.presentation.api.me import router as me_router

customer_portal_router_main = APIRouter()
customer_portal_router_main.include_router(admin_router)
customer_portal_router_main.include_router(auth_router)
customer_portal_router_main.include_router(me_router)
