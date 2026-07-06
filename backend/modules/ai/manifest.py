from core.module_registry.contracts import ModuleManifest
from modules.ai.navigation import AI_NAVIGATION
from modules.ai.permissions import AI_PERMISSIONS
from modules.ai.presentation.api.router import ai_router  # noqa: F401
from modules.ai.settings_schema import AI_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="ai",
    version="1.0.0",
    router=ai_router,
    permissions=AI_PERMISSIONS,
    depends_on=["crm", "catalog", "sales", "orders", "communication"],
    navigation=AI_NAVIGATION,
    settings_schema=AI_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.ai.infrastructure.models",
    migrations_path="modules/ai/infrastructure/migrations",
)
