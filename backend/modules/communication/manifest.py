from core.module_registry.contracts import ModuleManifest
from modules.communication.navigation import COMMUNICATION_NAVIGATION
from modules.communication.permissions import COMMUNICATION_PERMISSIONS
from modules.communication.presentation.api.router import communication_router  # noqa: F401
from modules.communication.settings_schema import COMMUNICATION_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="communication",
    version="1.0.0",
    router=communication_router,
    permissions=COMMUNICATION_PERMISSIONS,
    depends_on=["crm", "sales", "orders"],
    navigation=COMMUNICATION_NAVIGATION,
    settings_schema=COMMUNICATION_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.communication.infrastructure.models",
    migrations_path="modules/communication/infrastructure/migrations",
)
