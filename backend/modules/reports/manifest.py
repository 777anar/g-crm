from core.module_registry.contracts import ModuleManifest
from modules.reports.navigation import REPORTS_NAVIGATION
from modules.reports.permissions import REPORTS_PERMISSIONS
from modules.reports.presentation.api.router import reports_router_main  # noqa: F401
from modules.reports.settings_schema import REPORTS_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="reports",
    version="1.0.0",
    router=reports_router_main,
    permissions=REPORTS_PERMISSIONS,
    depends_on=["crm", "catalog", "sales", "orders", "installation"],
    navigation=REPORTS_NAVIGATION,
    settings_schema=REPORTS_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package=None,
    migrations_path=None,
)
