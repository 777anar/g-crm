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
