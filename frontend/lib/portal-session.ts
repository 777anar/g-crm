"use client";

// A separate localStorage namespace from lib/session.ts (staff auth) -- a
// customer and a staff member could legitimately be signed into the same
// browser at once (e.g. a G-STONE employee checking what a customer sees),
// so the two sessions must never share storage keys or collide.
const PORTAL_ACCESS_TOKEN_KEY = "g_erp_portal_access_token";
const PORTAL_REFRESH_TOKEN_KEY = "g_erp_portal_refresh_token";

export function getPortalAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(PORTAL_ACCESS_TOKEN_KEY);
}

export function setPortalAccessToken(token: string): void {
  window.localStorage.setItem(PORTAL_ACCESS_TOKEN_KEY, token);
}

export function getPortalRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(PORTAL_REFRESH_TOKEN_KEY);
}

export function setPortalRefreshToken(token: string): void {
  window.localStorage.setItem(PORTAL_REFRESH_TOKEN_KEY, token);
}

export function clearPortalTokens(): void {
  window.localStorage.removeItem(PORTAL_ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(PORTAL_REFRESH_TOKEN_KEY);
}
