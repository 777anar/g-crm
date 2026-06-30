from core.module_registry.contracts import ModuleManifest
from modules.crm.navigation import CRM_NAVIGATION
from modules.crm.permissions import CRM_PERMISSIONS
from modules.crm.presentation.api.router import crm_router
from modules.crm.settings_schema import CRM_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="crm",
    version="1.0.0",
    router=crm_router,
    permissions=CRM_PERMISSIONS,
    depends_on=[],
    navigation=CRM_NAVIGATION,
    settings_schema=CRM_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.crm.infrastructure.models",
    migrations_path="modules/crm/infrastructure/migrations",
)
