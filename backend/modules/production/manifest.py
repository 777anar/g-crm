from core.module_registry.contracts import ModuleManifest
from modules.production.navigation import PRODUCTION_NAVIGATION
from modules.production.permissions import PRODUCTION_PERMISSIONS
from modules.production.presentation.api.router import production_router_main  # noqa: F401
from modules.production.settings_schema import PRODUCTION_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="production",
    version="1.0.0",
    router=production_router_main,
    permissions=PRODUCTION_PERMISSIONS,
    depends_on=["crm", "catalog", "sales", "orders"],
    navigation=PRODUCTION_NAVIGATION,
    settings_schema=PRODUCTION_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.production.infrastructure.models",
    migrations_path="modules/production/infrastructure/migrations",
)
