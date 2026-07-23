"use client";

// A separate localStorage namespace from lib/session.ts (staff auth) -- a
// customer and a staff member could legitimately be signed into the same
// browser at once (e.g. a G-STONE employee checking what a customer sees),
// so the two sessions must never share storage keys or collide.
//
// Phase 18: the portal access/refresh JWTs are no longer stored here --
// the backend issues them as httpOnly cookies instead (see
// modules/customer_portal/presentation/api/auth.py). This module now only
// holds a non-sensitive "a portal session might be active" flag for
// optimistic route-guard decisions; the backend remains the sole real
// authority on every request via the cookie.
const PORTAL_SESSION_ACTIVE_KEY = "g_erp_portal_session_active";

export function hasPortalSession(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(PORTAL_SESSION_ACTIVE_KEY) === "1";
}

export function markPortalSessionActive(): void {
  window.localStorage.setItem(PORTAL_SESSION_ACTIVE_KEY, "1");
}

export function clearPortalSession(): void {
  window.localStorage.removeItem(PORTAL_SESSION_ACTIVE_KEY);
}
