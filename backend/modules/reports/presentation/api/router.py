from fastapi import APIRouter

from modules.reports.presentation.api.reports import router as reports_router

reports_router_main = reports_router
