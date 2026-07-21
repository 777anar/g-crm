from core.module_registry.contracts import ModuleManifest
from modules.marketing.navigation import MARKETING_NAVIGATION
from modules.marketing.permissions import MARKETING_PERMISSIONS
from modules.marketing.presentation.api.router import marketing_router_main  # noqa: F401
from modules.marketing.settings_schema import MARKETING_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="marketing",
    version="1.0.0",
    router=marketing_router_main,
    permissions=MARKETING_PERMISSIONS,
    # Read-only cross-module queries for campaign performance/attribution
    # (crm_leads, orders) -- the same "depends_on for read access" pattern
    # Reports uses, not a write-side coupling.
    depends_on=["crm", "orders"],
    navigation=MARKETING_NAVIGATION,
    settings_schema=MARKETING_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.marketing.infrastructure.models",
    migrations_path="modules/marketing/infrastructure/migrations",
)
