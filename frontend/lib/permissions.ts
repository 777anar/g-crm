"use client";

import { useEffect, useState } from "react";
import { getSessionClaims } from "./session";

// Mirrors backend/core/rbac/permissions.py's role hierarchy and action-suffix
// convention exactly, so a permission check here agrees with what the
// backend will actually enforce for the same session.
const ROLE_RANK: Record<string, number> = { viewer: 0, rep: 1, manager: 2, owner: 3 };
const ACTION_MIN_ROLE: Record<string, string> = {
  read: "viewer",
  write: "rep",
  approve: "manager",
  "settings:read": "manager",
  "settings:write": "owner",
};

function actionSuffix(permission: string): string {
  const parts = permission.split(":");
  if (parts.length >= 3 && parts[parts.length - 2] === "settings") {
    return `settings:${parts[parts.length - 1]}`;
  }
  return parts[parts.length - 1];
}

/** Synchronous permission check against the current session's claims
 * (lib/session.ts's `getSessionClaims()` -- role/module_permissions/
 * active_company_id returned in the login/select-company/refresh response
 * bodies, not decoded from a token: Phase 18 moved the actual JWTs into
 * httpOnly cookies, unreadable by JS). Prefer `usePermission()` in
 * components -- calling this directly during a server-rendered first paint
 * would read `null` (no `window`) and diverge from the post-hydration
 * client value, the same hydration-mismatch class `useLocalStorageState`/
 * `useUrlFilters` already guard against elsewhere in this codebase. */
export function hasPermission(permission: string): boolean {
  const claims = getSessionClaims();
  const role = claims?.role;
  if (!role) return false;

  const moduleName = permission.split(":")[0];
  const overrides = claims?.module_permissions?.[moduleName] ?? [];
  if (overrides.includes(permission)) return true;

  const action = actionSuffix(permission);
  const minRole = ACTION_MIN_ROLE[action] ?? "owner";
  return (ROLE_RANK[role] ?? -1) >= ROLE_RANK[minRole];
}

/** React hook wrapping `hasPermission()`, mount-only (matching this
 * codebase's established SSR-safe hydration pattern): renders `false` on
 * the server and first client paint, then resolves to the real value from
 * the stored session claims once mounted. A UX affordance only -- hiding a
 * control a user can't use -- never the authorization boundary itself,
 * which remains entirely server-side. */
export function usePermission(permission: string): boolean {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    setAllowed(hasPermission(permission));
  }, [permission]);

  return allowed;
}
