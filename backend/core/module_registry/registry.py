"""Discovers and mounts module plugins onto the core FastAPI app.

This is the one place in the core that touches module code -- and even
here, it only ever imports a single, well-known attribute
(`MODULE_MANIFEST`) from each module's top-level package. It never imports
a module's domain/application/infrastructure internals. This keeps the
dependency direction strictly core <- module (modules depend on core,
never the reverse), satisfying "core must never depend on any business
module."

Which modules are installed in a given deployment is controlled by
`INSTALLED_MODULES` below -- a plain list of package names. Adding a module
to this list (and nowhere else in core/) is the entire "install" step.
"""
import importlib
import logging
from typing import List

from fastapi import FastAPI

from core.events.event_bus import event_bus
from core.module_registry.contracts import ModuleManifest
from core.rbac.permissions import register_module_permissions

logger = logging.getLogger("core.module_registry")

# Step 1 (Core Platform) proved the core boots with zero modules. Phase 2
# installed CRM -- the first production business module. Version 2.0 adds
# Stone Catalog, per ROADMAP.md's approved dependency chain (CRM -> Tasks &
# Reminders -> Stone Catalog -> Sales). Later modules are appended here as
# their phase begins; no other core file changes when that happens.
INSTALLED_MODULES: List[str] = [
    "modules.crm",
    "modules.catalog",
    "modules.sales",
    "modules.orders",
    "modules.production",
    "modules.installation",
    "modules.finance",
    "modules.communication",
    "modules.reports",
    "modules.ai",
    "modules.purchasing",
    "modules.marketing",
    "modules.customer_portal",
    "modules.cut_optimization",
]

_loaded_manifests: List[ModuleManifest] = []


def _import_manifest(module_package: str) -> ModuleManifest:
    module = importlib.import_module(module_package)
    manifest = getattr(module, "MODULE_MANIFEST", None)
    if manifest is None:
        raise RuntimeError(
            f"Module '{module_package}' does not expose a MODULE_MANIFEST. "
            "Every installed module must define one (see core.module_registry.contracts.ModuleManifest)."
        )
    return manifest


def _validate_dependencies(manifests: List[ModuleManifest]) -> None:
    loaded_names = {m.name for m in manifests}
    for manifest in manifests:
        missing = [dep for dep in manifest.depends_on if dep not in loaded_names]
        if missing:
            raise RuntimeError(
                f"Module '{manifest.name}' depends on {missing}, which are not installed. "
                f"Add the missing module(s) to INSTALLED_MODULES before '{manifest.name}'."
            )


def load_manifests() -> List[ModuleManifest]:
    manifests = [_import_manifest(pkg) for pkg in INSTALLED_MODULES]
    _validate_dependencies(manifests)
    return manifests


def register_modules(app: FastAPI) -> List[ModuleManifest]:
    manifests = load_manifests()
    for manifest in manifests:
        app.include_router(manifest.router, prefix=f"/api/v1/{manifest.name}", tags=[manifest.name])
        register_module_permissions(manifest.name, manifest.permissions)
        for event_name, handlers in manifest.event_subscriptions.items():
            for handler in handlers:
                event_bus.subscribe(event_name, handler)
        logger.info("Mounted module '%s' v%s", manifest.name, manifest.version)
        _loaded_manifests.append(manifest)
    return manifests


def get_navigation_for_modules(enabled_module_names: List[str]) -> List[dict]:
    """Used by the frontend's nav-config endpoint: returns only the nav
    entries for modules a given company has enabled."""
    nav = []
    for manifest in _loaded_manifests:
        if manifest.name in enabled_module_names:
            nav.extend(manifest.navigation)
    return nav


def get_loaded_manifests() -> List[ModuleManifest]:
    return list(_loaded_manifests)
