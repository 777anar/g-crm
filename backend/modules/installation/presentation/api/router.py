from fastapi import APIRouter

from modules.installation.presentation.api.crews import router as crews_router
from modules.installation.presentation.api.installation_jobs import router as jobs_router
from modules.installation.presentation.api.notifications import router as notifications_router
from modules.installation.presentation.api.webhooks import router as webhooks_router

installation_router_main = APIRouter()
installation_router_main.include_router(jobs_router, prefix="/jobs")
installation_router_main.include_router(crews_router, prefix="/crews")
installation_router_main.include_router(notifications_router, prefix="/notifications")
installation_router_main.include_router(webhooks_router, prefix="/webhooks")
