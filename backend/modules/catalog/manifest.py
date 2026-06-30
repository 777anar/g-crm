from core.module_registry.contracts import ModuleManifest
from modules.catalog.navigation import CATALOG_NAVIGATION
from modules.catalog.permissions import CATALOG_PERMISSIONS
from modules.catalog.presentation.api.router import catalog_router
from modules.catalog.settings_schema import CATALOG_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="catalog",
    version="1.0.0",
    router=catalog_router,
    permissions=CATALOG_PERMISSIONS,
    depends_on=[],
    navigation=CATALOG_NAVIGATION,
    settings_schema=CATALOG_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.catalog.infrastructure.models",
    migrations_path="modules/catalog/infrastructure/migrations",
)
