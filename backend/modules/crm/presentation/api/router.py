from fastapi import APIRouter

from modules.crm.presentation.api.customers import router as customers_router
from modules.crm.presentation.api.leads import router as leads_router
from modules.crm.presentation.api.task_notifications import router as task_notifications_router
from modules.crm.presentation.api.tasks import router as tasks_router

crm_router = APIRouter()
crm_router.include_router(customers_router)
crm_router.include_router(leads_router)
crm_router.include_router(tasks_router)
crm_router.include_router(task_notifications_router)
