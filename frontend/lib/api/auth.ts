import { apiRequest } from "../api-client";
import type { LoginResponse } from "../types";

export function login(email: string, password: string) {
  return apiRequest<LoginResponse>("/api/v1/auth/login", { method: "POST", body: { email, password } });
}

export function selectCompany(companyId: string) {
  return apiRequest<{ access_token: string }>("/api/v1/auth/select-company", {
    method: "POST",
    body: { company_id: companyId },
  });
}

/** Revokes every refresh token issued to this user before now ("logout
 * everywhere"), not just a client-side token discard -- see the backend's
 * core/auth/token_denylist.py. Best-effort: the caller should still clear
 * local tokens and redirect even if this request fails. */
export function logout(refreshToken: string) {
  return apiRequest<{ status: string }>("/api/v1/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
  });
}

export function me() {
  return apiRequest<{
    id: string;
    email: string;
    full_name: string;
    active_company_id: string | null;
    role: string | null;
    module_permissions: Record<string, string[]>;
  }>("/api/v1/auth/me");
}
