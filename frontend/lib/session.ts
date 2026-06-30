"use client";

const ACCESS_TOKEN_KEY = "g_erp_access_token";

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

export function clearAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}
