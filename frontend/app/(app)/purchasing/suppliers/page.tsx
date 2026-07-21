"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { createSupplier, listSuppliers, updateSupplier } from "@/lib/api/purchasing";
import type { Supplier } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EntityStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/field";
import { SectionTabs } from "@/components/ui/section-tabs";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";

const CREATE_FORM_NAME_INPUT_ID = "supplier-create-name";

export default function SuppliersPage() {
  const t = useTranslations("purchasing");
  const tCommon = useTranslations("common");
  const [suppliers, setSuppliers] = useState<Supplier[] | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  const [name, setName] = useState("");
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(
    async (options: { append?: boolean; cursor?: string } = {}) => {
      try {
        const res = await listSuppliers({ search, includeHidden: true, cursor: options.cursor });
        setSuppliers((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
        setNextCursor(res.next_cursor);
      } catch (err) {
        setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
      }
    },
    [search, t]
  );

  async function handleToggleStatus(supplier: Supplier) {
    try {
      const updated = await updateSupplier(supplier.id, {
        status: supplier.status === "active" ? "hidden" : "active",
      });
      setSuppliers((prev) => prev?.map((s) => (s.id === updated.id ? updated : s)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("updateFailed"));
    }
  }

  useEffect(() => {
    setSuppliers(null);
    reload();
  }, [reload]);

  useListShortcuts({
    searchInputRef,
    onCreate: () => document.getElementById(CREATE_FORM_NAME_INPUT_ID)?.focus(),
  });

  function handleLoadMore() {
    if (!nextCursor) return;
    reload({ append: true, cursor: nextCursor });
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createSupplier({
        name,
        contact_name: contactName || undefined,
        phone: phone || undefined,
        email: email || undefined,
      });
      setName("");
      setContactName("");
      setPhone("");
      setEmail("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SectionTabs
        items={[
          { label: t("tabSuppliers"), href: "/purchasing/suppliers" },
          { label: t("tabPurchaseOrders"), href: "/purchasing/orders" },
        ]}
      />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("suppliersTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("suppliersSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("createSupplier")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" onSubmit={handleCreate}>
          <TextField
            id={CREATE_FORM_NAME_INPUT_ID}
            label={t("name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <TextField label={t("contactName")} value={contactName} onChange={(e) => setContactName(e.target.value)} />
          <TextField label={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value)} />
          <TextField label={t("email")} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <div className="flex items-end lg:col-span-4">
            <Button type="submit" disabled={submitting || !name}>
              {submitting ? t("creating") : t("createSupplier")}
            </Button>
          </div>
        </form>
      </Card>

      <input
        ref={searchInputRef}
        type="search"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder={t("searchSuppliersPlaceholder")}
        className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {suppliers === null && !error && <TableSkeleton rows={4} columns={5} />}

      {suppliers && suppliers.length === 0 && (
        <EmptyState title={t("noSuppliersYet")} description={t("noSuppliersDesc")} />
      )}

      {suppliers && suppliers.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("name")}</th>
                  <th className="px-4 py-2 font-medium">{t("contactName")}</th>
                  <th className="px-4 py-2 font-medium">{t("phone")}</th>
                  <th className="px-4 py-2 font-medium">{t("email")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {suppliers.map((supplier) => (
                  <tr key={supplier.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-medium text-text-primary">{supplier.name}</td>
                    <td className="px-4 py-2 text-text-secondary">{supplier.contact_name ?? tCommon("dash")}</td>
                    <td className="px-4 py-2 text-text-secondary">{supplier.phone ?? tCommon("dash")}</td>
                    <td className="px-4 py-2 text-text-secondary">{supplier.email ?? tCommon("dash")}</td>
                    <td className="px-4 py-2">
                      <EntityStatusBadge status={supplier.status} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button variant="secondary" onClick={() => handleToggleStatus(supplier)}>
                        {supplier.status === "active" ? t("entityStatus.hidden") : t("entityStatus.active")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleLoadMore}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
