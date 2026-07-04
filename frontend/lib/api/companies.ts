import { apiRequest } from "../api-client";
import type { Company, CompanyUser } from "../types";

export function listMyCompanies() {
  return apiRequest<Company[]>("/api/v1/core/companies");
}

export function listCompanyUsers() {
  return apiRequest<CompanyUser[]>("/api/v1/core/companies/users");
}
