"""Generic RBAC engine. The core enforces permissions; it never hardcodes
which permissions exist for a given module -- modules register their own
permission names via their manifest's `permissions` declaration (see
core.module_registry). This file defines the role hierarchy and the
generic check, not any module's specific permission strings.
"""
from typing import Dict, List, Optional

from core.auth.models import ROLE_MANAGER, ROLE_OWNER, ROLE_REP, ROLE_VIEWER

# Action -> minimum role tier required, by convention every permission string
# ends in one of these action suffixes: "<module>:<resource>:<action>".
_ACTION_MIN_ROLE: Dict[str, str] = {
    "read": ROLE_VIEWER,
    "write": ROLE_REP,
    "approve": ROLE_MANAGER,
    "settings:read": ROLE_MANAGER,
    "settings:write": ROLE_OWNER,
}

_ROLE_RANK = {ROLE_VIEWER: 0, ROLE_REP: 1, ROLE_MANAGER: 2, ROLE_OWNER: 3}

# Registry of permission names contributed by installed modules, populated by
# the module registry at startup. Used only for validation/introspection
# (e.g., detecting collisions) -- enforcement itself is purely structural
# (parsing the action suffix), so the core never needs to know what "crm" or
# "deals" mean.
_REGISTERED_PERMISSIONS: Dict[str, str] = {}


def register_module_permissions(module_name: str, permissions: List[str]) -> None:
    for permission in permissions:
        existing_owner = _REGISTERED_PERMISSIONS.get(permission)
        if existing_owner and existing_owner != module_name:
            raise ValueError(
                f"Permission '{permission}' is already registered by module '{existing_owner}'; "
                f"module '{module_name}' cannot reuse it."
            )
        _REGISTERED_PERMISSIONS[permission] = module_name


def _action_suffix(permission: str) -> str:
    parts = permission.split(":")
    if len(parts) >= 3 and parts[-2] == "settings":
        return "settings:" + parts[-1]
    return parts[-1]


def role_has_permission(
    *,
    role: Optional[str],
    permission: str,
    module_permission_overrides: Optional[Dict[str, List[str]]] = None,
) -> bool:
    if role is None:
        return False

    module_permission_overrides = module_permission_overrides or {}
    module_name = permission.split(":", 1)[0]
    if permission in module_permission_overrides.get(module_name, []):
        return True

    action = _action_suffix(permission)
    min_role = _ACTION_MIN_ROLE.get(action, ROLE_OWNER)
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK[min_role]
