"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listProjects, createProject } from "@/lib/api/sales";
import { listCustomers } from "@/lib/api/crm";
import type { Customer, Project } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { useDebouncedValue } from "@/lib/use-debounced-value";

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
    } catch {
      setSubmitting(false);
    }
  }

  function customerName(id: string) {
    return customers.find((c) => c.id === id)?.name ?? id;
  }

  const PROJECT_TYPES = ["kitchen", "bathroom", "stairs", "floor", "cladding", "outdoor", "other"];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("projectsTitle")}</h1>
          <p className="page-subtitle">{t("projectsSubtitle")}</p>
        </div>
        <Button onClick={() => setShowNewForm(!showNewForm)}>{t("createProject")}</Button>
      </div>

      {showNewForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="form-grid">
            <div className="form-field">
              <label>{t("customer")}</label>
              <select
                className="input"
                value={form.customer_id}
                onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
                required
              >
                <option value="">{tCommon("select")}…</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label>{t("projectName")}</label>
              <input
                className="input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="form-field">
              <label>{t("projectType")}</label>
              <select
                className="input"
                value={form.project_type}
                onChange={(e) => setForm({ ...form, project_type: e.target.value })}
              >
                {PROJECT_TYPES.map((pt) => (
                  <option key={pt} value={pt}>{t(`projectType_${pt}` as any)}</option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label>{t("address")}</label>
              <input
                className="input"
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={submitting}>
                {submitting ? t("creating") : tCommon("create")}
              </Button>
              <Button variant="secondary" type="button" onClick={() => setShowNewForm(false)}>
                {tCommon("cancel")}
              </Button>
            </div>
          </form>
        </div>
      )}

      <div className="search-bar mb-4">
        <input
          className="input"
          placeholder={t("searchProjectsPlaceholder")}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      {projects === null ? (
        <TableSkeleton />
      ) : projects.length === 0 ? (
        <EmptyState title={t("noProjectsYet")} description={t("noProjectsDesc")} />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("tableProject")}</th>
                <th>{t("projectType")}</th>
                <th>{t("tableCustomer")}</th>
                <th>{t("address")}</th>
                <th>{t("tableStatus")}</th>
                <th>{t("tableCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr
                  key={p.id}
                  className="clickable-row"
                  onClick={() => router.push(`/sales/projects/${p.id}`)}
                >
                  <td className="font-medium">{p.name}</td>
                  <td>{t(`projectType_${p.project_type || "other"}` as any)}</td>
                  <td>{customerName(p.customer_id)}</td>
                  <td>{p.address ?? tCommon("dash")}</td>
                  <td>
                    <span className={`status-badge status-${p.status}`}>{p.status}</span>
                  </td>
                  <td>{new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
