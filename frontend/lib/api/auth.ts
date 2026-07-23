import { apiRequest } from "../api-client";
import type { LoginResponse, TokenResponse } from "../types";

export function login(email: string, password: string) {
  return apiRequest<LoginResponse>("/api/v1/auth/login", { method: "POST", body: { email, password } });
}

export function verifyMfa(mfaToken: string, code: string) {
  return apiRequest<LoginResponse>("/api/v1/auth/mfa/verify", {
    method: "POST",
    body: { mfa_token: mfaToken, code },
  });
}

export function setupMfa() {
  return apiRequest<{ secret: string; otpauth_uri: string }>("/api/v1/auth/mfa/setup", { method: "POST" });
}

export function enableMfa(code: string) {
  return apiRequest<{ status: string; mfa_enabled: boolean }>("/api/v1/auth/mfa/enable", {
    method: "POST",
    body: { code },
  });
}

export function disableMfa(code: string) {
  return apiRequest<{ status: string; mfa_enabled: boolean }>("/api/v1/auth/mfa/disable", {
    method: "POST",
    body: { code },
  });
}

export function selectCompany(companyId: string) {
  return apiRequest<TokenResponse>("/api/v1/auth/select-company", {
    method: "POST",
    body: { company_id: companyId },
  });
}

/** Revokes every refresh token issued to this user before now ("logout
 * everywhere"), not just a client-side token discard -- see the backend's
 * core/auth/token_denylist.py. Best-effort: the caller should still clear
 * the local session flag and redirect even if this request fails. The
 * refresh token itself is never passed here (Phase 18): it lives only in
 * the httpOnly cookie, which the backend reads directly. */
export function logout() {
  return apiRequest<{ status: string }>("/api/v1/auth/logout", { method: "POST" });
}

export function me() {
  return apiRequest<{
    id: string;
    email: string;
    full_name: string;
    active_company_id: string | null;
    role: string | null;
    module_permissions: Record<string, string[]>;
    mfa_enabled: boolean;
  }>("/api/v1/auth/me");
}
