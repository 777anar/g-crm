import { apiDownload, apiRequest } from "../api-client";
import type {
  ExecutiveDashboard,
  FinanceAnalytics,
  InstallationAnalytics,
  InventoryAnalytics,
  ProductionAnalytics,
  ProductionPlanning,
  ReportPeriod,
  SalesAnalytics,
} from "../types";

const BASE = "/api/v1/reports";

export type ReportFilterParams = {
  period?: ReportPeriod;
  dateFrom?: string;
  dateTo?: string;
};

function searchParams(params: ReportFilterParams) {
  return {
    period: params.period,
    date_from: params.dateFrom,
    date_to: params.dateTo,
  };
}

export function getExecutiveDashboard(params: ReportFilterParams = {}) {
  return apiRequest<ExecutiveDashboard>(`${BASE}/executive`, { searchParams: searchParams(params) });
}

export function getSalesAnalytics(params: ReportFilterParams = {}) {
  return apiRequest<SalesAnalytics>(`${BASE}/sales`, { searchParams: searchParams(params) });
}

export function getProductionAnalytics(params: ReportFilterParams = {}) {
  return apiRequest<ProductionAnalytics>(`${BASE}/production`, { searchParams: searchParams(params) });
}

export function getInstallationAnalytics(params: ReportFilterParams = {}) {
  return apiRequest<InstallationAnalytics>(`${BASE}/installation`, { searchParams: searchParams(params) });
}

export function getFinanceAnalytics(params: ReportFilterParams = {}) {
  return apiRequest<FinanceAnalytics>(`${BASE}/finance`, { searchParams: searchParams(params) });
}

export function getInventoryAnalytics(params: ReportFilterParams = {}) {
  return apiRequest<InventoryAnalytics>(`${BASE}/inventory`, { searchParams: searchParams(params) });
}

export function getProductionPlanning() {
  return apiRequest<ProductionPlanning>(`${BASE}/production-planning`);
}

export type ReportType = "executive" | "sales" | "production" | "installation" | "finance" | "inventory";

export function exportReport(reportType: ReportType, format: "pdf" | "excel", params: ReportFilterParams = {}) {
  const extension = format === "pdf" ? "pdf" : "xlsx";
  return apiDownload(`${BASE}/${reportType}/export/${format}`, {
    searchParams: searchParams(params),
    filename: `${reportType}-report.${extension}`,
  });
}
