"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listProjects, createProject } from "@/lib/api/sales";
import { listCustomers } from "@/lib/api/crm";
import type { Customer, Project } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SelectField, TextField } from "@/components/ui/field";
import { ProjectStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const PROJECT_TYPES = ["kitchen", "bathroom", "commercial", "stairs", "fireplace", "other"];

export default function ProjectsPage() {
  const t = useTranslations("sales");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [projects, setProjects] = useState<Project[] | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", name: "", project_type: "other", address: "" });
  const [submitting, setSubmitting] = useState(false);
  const search = useDebouncedValue(searchInput, 250);

  useEffect(() => {
    listCustomers({ limit: 200 }).then((r) => setCustomers(r.items)).catch(() => {});
  }, []);

  const load = useCallback(() => {
    listProjects({ search: search || undefined })
      .then((r) => setProjects(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [search, t]);

  useEffect(() => {
    setProjects(null);
    load();
  }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.customer_id || !form.name) return;
    setSubmitting(true);
    try {
      const proj = await createProject({
        customer_id: form.customer_id,
        name: form.name,
        project_type: form.project_type,
        address: form.address || undefined,
      });
      router.push(`/sales/projects/${proj.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
      setSubmitting(false);
    }
  }

  function customerName(id: string) {
    return customers.find((c) => c.id === id)?.name ?? id;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("projectsTitle")}</h1>
          <p className="text-sm text-text-secondary">{t("projectsSubtitle")}</p>
        </div>
        <Button onClick={() => setShowNewForm(!showNewForm)}>{t("createProject")}</Button>
      </div>

      {showNewForm && (
        <Card>
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField
              label={t("customer")}
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              required
            >
              <option value="">{tCommon("select")}…</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </SelectField>
            <TextField
              label={t("projectName")}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <SelectField
              label={t("projectType")}
              value={form.project_type}
              onChange={(e) => setForm({ ...form, project_type: e.target.value })}
            >
              {PROJECT_TYPES.map((pt) => (
                <option key={pt} value={pt}>{t(`projectType_${pt}` as any)}</option>
              ))}
            </SelectField>
            <TextField
              label={t("address")}
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" disabled={submitting}>
                {submitting ? t("creating") : tCommon("create")}
              </Button>
              <Button variant="secondary" type="button" onClick={() => setShowNewForm(false)}>
                {tCommon("cancel")}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <input
        type="search"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder={t("searchProjectsPlaceholder")}
        className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {projects === null && !error && <TableSkeleton rows={5} columns={5} />}

      {projects && projects.length === 0 && (
        <EmptyState title={t("noProjectsYet")} description={t("noProjectsDesc")} />
      )}

      {projects && projects.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("tableProject")}</th>
                <th className="px-4 py-2 font-medium">{t("projectType")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCustomer")}</th>
                <th className="px-4 py-2 font-medium">{t("address")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => router.push(`/sales/projects/${p.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2 font-medium text-text-primary">{p.name}</td>
                  <td className="px-4 py-2">{t(`projectType_${p.project_type || "other"}` as any)}</td>
                  <td className="px-4 py-2 text-text-secondary">{customerName(p.customer_id)}</td>
                  <td className="px-4 py-2 text-text-secondary">{p.address ?? tCommon("dash")}</td>
                  <td className="px-4 py-2">
                    <ProjectStatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-2 text-text-secondary">{formatDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
