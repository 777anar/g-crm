from fastapi import APIRouter

from modules.ai.presentation.api.analysis import router as analysis_router
from modules.ai.presentation.api.dashboard import router as dashboard_router
from modules.ai.presentation.api.recommendations import router as recommendations_router

ai_router = APIRouter()
ai_router.include_router(analysis_router)
ai_router.include_router(recommendations_router)
ai_router.include_router(dashboard_router)
