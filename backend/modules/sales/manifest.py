from core.module_registry.contracts import ModuleManifest
from modules.sales.navigation import SALES_NAVIGATION
from modules.sales.permissions import SALES_PERMISSIONS
from modules.sales.presentation.api.router import sales_router
from modules.sales.settings_schema import SALES_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="sales",
    version="1.0.0",
    router=sales_router,
    permissions=SALES_PERMISSIONS,
    depends_on=["catalog", "crm"],
    navigation=SALES_NAVIGATION,
    settings_schema=SALES_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.sales.infrastructure.models",
    migrations_path="modules/sales/infrastructure/migrations",
)
