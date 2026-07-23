"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { createExpense, listExpenses } from "@/lib/api/finance";
import { EXPENSE_CATEGORIES, type Expense } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TextField, SelectField } from "@/components/ui/field";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { usePermission } from "@/lib/permissions";

const emptyForm = { category: "other", amount: "", expense_date: "", description: "" };

export default function ExpensesPage() {
  const t = useTranslations("finance");
  const tCommon = useTranslations("common");
  const canWrite = usePermission("finance:expenses:write");

  const [expenses, setExpenses] = useState<Expense[] | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(
    (options: { append?: boolean; cursor?: string } = {}) => {
      listExpenses({ category: categoryFilter || undefined, cursor: options.cursor })
        .then((r) => {
          setExpenses((prev) => (options.append && prev ? [...prev, ...r.items] : r.items));
          setNextCursor(r.next_cursor);
        })
        .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    },
    [categoryFilter, t]
  );

  useEffect(() => {
    setExpenses(null);
    load();
  }, [load]);

  function handleLoadMore() {
    if (!nextCursor) return;
    load({ append: true, cursor: nextCursor });
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.amount || !form.expense_date) return;
    setCreating(true);
    setCreateError(null);
    try {
      await createExpense({
        category: form.category,
        amount: form.amount,
        expense_date: form.expense_date,
        description: form.description || undefined,
      });
      setForm(emptyForm);
      load();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("expensesTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("expensesSubtitle")}</p>
      </div>

      {canWrite && (
      <Card>
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-3 md:grid-cols-5 md:items-end">
          <SelectField
            label={t("category")}
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          >
            {EXPENSE_CATEGORIES.map((c) => (
              <option key={c} value={c}>{t(`expenseCategory_${c}` as Parameters<typeof t>[0])}</option>
            ))}
          </SelectField>
          <TextField
            label={t("amount")}
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            placeholder="0.00"
          />
          <TextField
            label={t("expenseDate")}
            type="date"
            value={form.expense_date}
            onChange={(e) => setForm({ ...form, expense_date: e.target.value })}
          />
          <TextField
            label={t("description")}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Button type="submit" disabled={creating || !form.amount || !form.expense_date}>
            {creating ? t("saving") : t("addExpense")}
          </Button>
        </form>
        {createError && <p className="mt-2 text-sm text-danger">{createError}</p>}
      </Card>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="">{t("allCategories")}</option>
          {EXPENSE_CATEGORIES.map((c) => (
            <option key={c} value={c}>{t(`expenseCategory_${c}` as Parameters<typeof t>[0])}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}
      {expenses === null && !error && <TableSkeleton rows={4} columns={4} />}
      {expenses && expenses.length === 0 && (
        <EmptyState title={t("noExpensesYet")} description={t("noExpensesDesc")} />
      )}

      {expenses && expenses.length > 0 && (
        <>
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("expenseDate")}</th>
                <th className="px-4 py-2 font-medium">{t("category")}</th>
                <th className="px-4 py-2 font-medium">{t("description")}</th>
                <th className="px-4 py-2 font-medium">{t("amount")}</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((e) => (
                <tr key={e.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 text-text-secondary">{formatDate(e.expense_date)}</td>
                  <td className="px-4 py-2 text-text-primary">{t(`expenseCategory_${e.category}` as Parameters<typeof t>[0])}</td>
                  <td className="px-4 py-2 text-text-secondary">{e.description ?? tCommon("dash")}</td>
                  <td className="px-4 py-2 font-medium text-text-primary">{e.currency} {parseFloat(e.amount).toFixed(2)}</td>
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
