from core.module_registry.contracts import ModuleManifest
from modules.cut_optimization.navigation import CUT_OPTIMIZATION_NAVIGATION
from modules.cut_optimization.permissions import CUT_OPTIMIZATION_PERMISSIONS
from modules.cut_optimization.presentation.api.router import cut_optimization_router_main  # noqa: F401
from modules.cut_optimization.settings_schema import CUT_OPTIMIZATION_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="cut_optimization",
    version="1.0.0",
    router=cut_optimization_router_main,
    permissions=CUT_OPTIMIZATION_PERMISSIONS,
    depends_on=["catalog"],
    navigation=CUT_OPTIMIZATION_NAVIGATION,
    settings_schema=CUT_OPTIMIZATION_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.cut_optimization.infrastructure.models",
    migrations_path="modules/cut_optimization/infrastructure/migrations",
)
