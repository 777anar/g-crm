"use client";

// Phase 18 (Security & Compliance Hardening): the staff access/refresh JWTs
// themselves are no longer stored here -- the backend now issues them as
// httpOnly cookies (core/auth/router.py), unreadable by JS and therefore
// safe from XSS-based exfiltration. This module now only holds two kinds
// of non-sensitive, JS-readable state:
//   - a boolean "a session might be active" flag, used for optimistic
//     route-guard/redirect decisions (the backend remains the sole real
//     authority: every API call is still enforced server-side via the
//     cookie, regardless of what this flag says);
//   - the session's claims (role, module_permissions, active_company_id) --
//     metadata, not a bearer credential, returned in the login/select-company/
//     refresh response bodies specifically so lib/permissions.ts can still
//     gate UI without being able to decode an httpOnly token.
const SESSION_ACTIVE_KEY = "g_erp_session_active";
const CLAIMS_KEY = "g_erp_session_claims";

export type SessionClaims = {
  role: string | null;
  module_permissions: Record<string, string[]>;
  active_company_id: string | null;
};

export function hasSession(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(SESSION_ACTIVE_KEY) === "1";
}

export function markSessionActive(): void {
  window.localStorage.setItem(SESSION_ACTIVE_KEY, "1");
}

export function getSessionClaims(): SessionClaims | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(CLAIMS_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionClaims;
  } catch {
    return null;
  }
}

export function setSessionClaims(claims: Partial<SessionClaims>): void {
  const current = getSessionClaims() ?? { role: null, module_permissions: {}, active_company_id: null };
  const next: SessionClaims = { ...current, ...claims };
  window.localStorage.setItem(CLAIMS_KEY, JSON.stringify(next));
}

export function clearSession(): void {
  window.localStorage.removeItem(SESSION_ACTIVE_KEY);
  window.localStorage.removeItem(CLAIMS_KEY);
}
