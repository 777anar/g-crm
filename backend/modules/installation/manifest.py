from core.module_registry.contracts import ModuleManifest
from modules.installation.navigation import INSTALLATION_NAVIGATION
from modules.installation.permissions import INSTALLATION_PERMISSIONS
from modules.installation.presentation.api.router import installation_router_main  # noqa: F401
from modules.installation.settings_schema import INSTALLATION_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="installation",
    version="1.0.0",
    router=installation_router_main,
    permissions=INSTALLATION_PERMISSIONS,
    depends_on=["crm", "catalog", "sales", "orders"],
    navigation=INSTALLATION_NAVIGATION,
    settings_schema=INSTALLATION_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.installation.infrastructure.models",
    migrations_path="modules/installation/infrastructure/migrations",
)
