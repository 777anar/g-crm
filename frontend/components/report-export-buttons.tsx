"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { exportReport, type ReportFilterParams, type ReportType } from "@/lib/api/reports";
import { ApiRequestError } from "@/lib/api-client";

export function ReportExportButtons({
  reportType,
  filterParams,
}: {
  reportType: ReportType;
  filterParams: ReportFilterParams;
}) {
  const t = useTranslations("reports");
  const [exporting, setExporting] = useState<"pdf" | "excel" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport(format: "pdf" | "excel") {
    setExporting(format);
    setError(null);
    try {
      await exportReport(reportType, format, filterParams);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("exportFailed"));
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button variant="secondary" disabled={exporting !== null} onClick={() => handleExport("pdf")}>
        {exporting === "pdf" ? t("exporting") : t("exportPdf")}
      </Button>
      <Button variant="secondary" disabled={exporting !== null} onClick={() => handleExport("excel")}>
        {exporting === "excel" ? t("exporting") : t("exportExcel")}
      </Button>
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
