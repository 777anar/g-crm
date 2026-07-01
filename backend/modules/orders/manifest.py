from core.module_registry.contracts import ModuleManifest
from modules.orders.navigation import ORDERS_NAVIGATION
from modules.orders.permissions import ORDERS_PERMISSIONS
from modules.orders.presentation.api.router import orders_router_main  # noqa: F401
from modules.orders.settings_schema import ORDERS_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="orders",
    version="1.0.0",
    router=orders_router_main,
    permissions=ORDERS_PERMISSIONS,
    depends_on=["crm", "catalog", "sales"],
    navigation=ORDERS_NAVIGATION,
    settings_schema=ORDERS_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.orders.infrastructure.models",
    migrations_path="modules/orders/infrastructure/migrations",
)
