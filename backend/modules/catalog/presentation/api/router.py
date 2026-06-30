from fastapi import APIRouter

from modules.catalog.presentation.api.brands import router as brands_router
from modules.catalog.presentation.api.collections import router as collections_router
from modules.catalog.presentation.api.materials import router as materials_router
from modules.catalog.presentation.api.price_lists import router as price_lists_router
from modules.catalog.presentation.api.slabs import router as slabs_router
from modules.catalog.presentation.api.warehouses import router as warehouses_router

catalog_router = APIRouter()
catalog_router.include_router(brands_router)
catalog_router.include_router(collections_router)
catalog_router.include_router(materials_router)
catalog_router.include_router(warehouses_router)
catalog_router.include_router(slabs_router)
catalog_router.include_router(price_lists_router)
