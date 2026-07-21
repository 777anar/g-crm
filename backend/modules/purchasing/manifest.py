from core.module_registry.contracts import ModuleManifest
from modules.purchasing.navigation import PURCHASING_NAVIGATION
from modules.purchasing.permissions import PURCHASING_PERMISSIONS
from modules.purchasing.presentation.api.router import purchasing_router_main  # noqa: F401
from modules.purchasing.settings_schema import PURCHASING_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="purchasing",
    version="1.0.0",
    router=purchasing_router_main,
    permissions=PURCHASING_PERMISSIONS,
    depends_on=["catalog"],
    navigation=PURCHASING_NAVIGATION,
    settings_schema=PURCHASING_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.purchasing.infrastructure.models",
    migrations_path="modules/purchasing/infrastructure/migrations",
)
