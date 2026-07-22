"use client";

import { useEffect, useState } from "react";
import { getAccessToken } from "./session";

// Mirrors backend/core/rbac/permissions.py's role hierarchy and action-suffix
// convention exactly, so a permission check here agrees with what the
// backend will actually enforce for the same access token.
const ROLE_RANK: Record<string, number> = { viewer: 0, rep: 1, manager: 2, owner: 3 };
const ACTION_MIN_ROLE: Record<string, string> = {
  read: "viewer",
  write: "rep",
  approve: "manager",
  "settings:read": "manager",
  "settings:write": "owner",
};

type AccessTokenClaims = {
  role?: string | null;
  module_permissions?: Record<string, string[]>;
};

/** Decodes (without verifying) the current access token's `role`/
 * `module_permissions` claims -- the same claims `core/auth/security.py`'s
 * `create_access_token` embeds and `core/rbac/dependencies.py` reads server
 * side. Used only to drive UI affordances, never as an authorization
 * decision of its own: every write endpoint still enforces
 * `require_permission` independently regardless of what this returns. */
function decodeAccessTokenClaims(): AccessTokenClaims {
  const token = getAccessToken();
  if (!token) return {};
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as AccessTokenClaims;
  } catch {
    return {};
  }
}

function actionSuffix(permission: string): string {
  const parts = permission.split(":");
  if (parts.length >= 3 && parts[parts.length - 2] === "settings") {
    return `settings:${parts[parts.length - 1]}`;
  }
  return parts[parts.length - 1];
}

/** Synchronous permission check against the current access token. Prefer
 * `usePermission()` in components -- calling this directly during a
 * server-rendered first paint would read `null` (no `window`) and diverge
 * from the post-hydration client value, the same hydration-mismatch class
 * `useLocalStorageState`/`useUrlFilters` already guard against elsewhere in
 * this codebase. */
export function hasPermission(permission: string): boolean {
  const { role, module_permissions } = decodeAccessTokenClaims();
  if (!role) return false;

  const moduleName = permission.split(":")[0];
  const overrides = module_permissions?.[moduleName] ?? [];
  if (overrides.includes(permission)) return true;

  const action = actionSuffix(permission);
  const minRole = ACTION_MIN_ROLE[action] ?? "owner";
  return (ROLE_RANK[role] ?? -1) >= ROLE_RANK[minRole];
}

/** React hook wrapping `hasPermission()`, mount-only (matching this
 * codebase's established SSR-safe hydration pattern): renders `false` on
 * the server and first client paint, then resolves to the real value from
 * the access token once mounted. A UX affordance only -- hiding a control a
 * user can't use -- never the authorization boundary itself, which remains
 * entirely server-side. */
export function usePermission(permission: string): boolean {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    setAllowed(hasPermission(permission));
  }, [permission]);

  return allowed;
}
