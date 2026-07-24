"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { downloadSupplierCatalogImportTemplate, importSupplierCatalog } from "@/lib/api/catalog";
import type { SupplierCatalogImportSummary } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ApiRequestError } from "@/lib/api-client";

export default function SupplierCatalogImportPage() {
  const t = useTranslations("catalog");
  const tNav = useTranslations("nav");

  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [summary, setSummary] = useState<SupplierCatalogImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDownloadTemplate() {
    setDownloading(true);
    try {
      await downloadSupplierCatalogImportTemplate();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("importFailed"));
    } finally {
      setDownloading(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setSummary(null);
    try {
      const result = await importSupplierCatalog(file);
      setSummary(result);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("importFailed"));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        items={[
          { label: tNav("catalog"), href: "/catalog/materials" },
          { label: t("tabMaterials"), href: "/catalog/materials" },
          { label: t("importTitle") },
        ]}
      />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("importTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("importSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("importStep1")} />
        <p className="mb-3 text-sm text-text-secondary">{t("importTemplateDesc")}</p>
        <Button variant="secondary" onClick={handleDownloadTemplate} loading={downloading}>
          {t("downloadTemplate")}
        </Button>
      </Card>

      <Card>
        <CardHeader title={t("importStep2")} />
        <p className="mb-3 text-sm text-text-secondary">{t("importUploadDesc")}</p>
        <label className="inline-flex">
          <span className="sr-only">{t("uploadCsv")}</span>
          <input type="file" accept=".csv,text/csv" onChange={handleUpload} disabled={uploading} className="text-sm" />
        </label>
        {uploading && <span className="ml-2 text-sm text-text-secondary">{t("importing")}</span>}
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {summary && (
        <Card>
          <CardHeader title={t("importResultsTitle")} />
          <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
            <div>
              <p className="text-xs text-text-secondary">{t("importBrandsCreated")}</p>
              <p className="text-lg font-semibold text-text-primary">{summary.brands_created}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("importMaterialsCreated")}</p>
              <p className="text-lg font-semibold text-text-primary">{summary.materials_created}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("importMaterialsUpdated")}</p>
              <p className="text-lg font-semibold text-text-primary">{summary.materials_updated}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("importThicknessesAdded")}</p>
              <p className="text-lg font-semibold text-text-primary">{summary.thicknesses_added}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("importSizesAdded")}</p>
              <p className="text-lg font-semibold text-text-primary">{summary.sizes_added}</p>
            </div>
          </div>

          {summary.errors.length > 0 && (
            <div className="rounded-md border border-danger/30 bg-danger/5 p-3">
              <p className="text-sm font-medium text-danger">{t("importRowErrors")}</p>
              <ul className="mt-1 list-disc pl-5 text-sm text-danger">
                {summary.errors.map((e, i) => (
                  <li key={i}>{t("importRowLabel", { row: e.row_number })}: {e.message}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
