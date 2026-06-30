import { apiRequest } from "../api-client";
import type { Company } from "../types";

export function listMyCompanies() {
  return apiRequest<Company[]>("/api/v1/core/companies");
}
