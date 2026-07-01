from fastapi import APIRouter

from modules.sales.presentation.api.items import router as items_router
from modules.sales.presentation.api.measurements import router as measurements_router
from modules.sales.presentation.api.pdf import router as pdf_router
from modules.sales.presentation.api.projects import router as projects_router
from modules.sales.presentation.api.quotes import router as quotes_router
from modules.sales.presentation.api.sections import router as sections_router
from modules.sales.presentation.api.service_prices import router as service_prices_router

sales_router = APIRouter()
sales_router.include_router(projects_router)
sales_router.include_router(quotes_router)
sales_router.include_router(sections_router)
sales_router.include_router(measurements_router)
sales_router.include_router(items_router)
sales_router.include_router(service_prices_router)
sales_router.include_router(pdf_router)
