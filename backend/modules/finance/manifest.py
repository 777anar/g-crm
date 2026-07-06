from core.module_registry.contracts import ModuleManifest
from modules.finance.navigation import FINANCE_NAVIGATION
from modules.finance.permissions import FINANCE_PERMISSIONS
from modules.finance.presentation.api.router import finance_router_main  # noqa: F401
from modules.finance.settings_schema import FINANCE_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="finance",
    version="1.0.0",
    router=finance_router_main,
    permissions=FINANCE_PERMISSIONS,
    depends_on=["crm", "catalog", "sales", "orders", "installation"],
    navigation=FINANCE_NAVIGATION,
    settings_schema=FINANCE_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.finance.infrastructure.models",
    migrations_path="modules/finance/infrastructure/migrations",
)
