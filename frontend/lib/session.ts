"use client";

const ACCESS_TOKEN_KEY = "g_erp_access_token";
const REFRESH_TOKEN_KEY = "g_erp_refresh_token";

// Client-side token storage. Phase 2 scope: simple localStorage persistence.
// A future hardening pass can move the refresh token to an httpOnly cookie
// set by a Next.js route handler; the access token must stay readable by
// client code regardless, since it is attached to every fetch() call here.
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/** Reads the `active_company_id` claim out of a JWT's payload without
 * verifying its signature -- used only to carry the previously active
 * company across a silent token refresh, never for authorization. */
export function decodeActiveCompanyId(token: string): string | null {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json) as { active_company_id?: string | null };
    return claims.active_company_id ?? null;
  } catch {
    return null;
  }
}
