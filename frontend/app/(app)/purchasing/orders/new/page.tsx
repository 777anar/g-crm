"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { PurchasingTabs } from "@/components/purchasing-tabs";
import { createPurchaseOrder } from "@/lib/api/purchasing";
import { listSuppliers } from "@/lib/api/purchasing";
import { listBrands, listMaterials } from "@/lib/api/catalog";
import type { Brand, Material, Supplier } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { TextField, TextAreaField, SelectField } from "@/components/ui/field";
import { ApiRequestError } from "@/lib/api-client";

type DraftLine = {
  key: number;
  materialId: string;
  description: string;
  quantity: string;
  unit: string;
  unitCost: string;
};

let nextKey = 1;

function emptyLine(): DraftLine {
  return { key: nextKey++, materialId: "", description: "", quantity: "1", unit: "unit", unitCost: "0" };
}

export default function NewPurchaseOrderPage() {
  const t = useTranslations("purchasing");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);

  const [supplierId, setSupplierId] = useState("");
  const [currency, setCurrency] = useState("AZN");
  const [notes, setNotes] = useState("");
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSuppliers({ limit: 100 }).then((res) => setSuppliers(res.items)).catch(() => {});
    listMaterials({ limit: 100 }).then((res) => setMaterials(res.items)).catch(() => {});
    listBrands().then((res) => setBrands(res.items)).catch(() => {});
  }, []);

  // Prefill the first line from a Reports > Inventory low-stock suggestion
  // link (Phase 20: `?material_id=...&description=...`) -- read directly
  // from the URL rather than useSearchParams so this client page doesn't
  // need a Suspense boundary just for a one-time prefill.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const materialId = params.get("material_id");
    const description = params.get("description");
    if (!materialId && !description) return;
    setLines((prev) => [
      { ...prev[0], materialId: materialId ?? prev[0].materialId, description: description ?? prev[0].description },
      ...prev.slice(1),
    ]);
  }, []);

  function brandName(id: string) {
    return brands.find((b) => b.id === id)?.name ?? "";
  }

  function updateLine(key: number, patch: Partial<DraftLine>) {
    setLines((prev) => prev.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine()]);
  }

  function removeLine(key: number) {
    setLines((prev) => (prev.length > 1 ? prev.filter((line) => line.key !== key) : prev));
  }

  const total = lines.reduce((sum, line) => {
    const qty = parseFloat(line.quantity) || 0;
    const cost = parseFloat(line.unitCost) || 0;
    return sum + qty * cost;
  }, 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supplierId || lines.some((l) => !l.description || !l.quantity)) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createPurchaseOrder({
        supplier_id: supplierId,
        currency,
        notes: notes || undefined,
        expected_delivery_date: expectedDeliveryDate || undefined,
        lines: lines.map((l) => ({
          material_id: l.materialId || undefined,
          description: l.description,
          quantity: l.quantity,
          unit: l.unit || "unit",
          unit_cost: l.unitCost || "0",
        })),
      });
      router.push(`/purchasing/orders/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PurchasingTabs />
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("createOrder")}</h1>
        <p className="text-sm text-text-secondary">{t("createOrderSubtitle")}</p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        <Card>
          <CardHeader title={t("orderDetails")} />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <SelectField
              label={t("supplier")}
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              required
            >
              <option value="">{tCommon("select")}</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </SelectField>
            <TextField label={t("currency")} value={currency} onChange={(e) => setCurrency(e.target.value)} maxLength={3} />
            <TextField
              label={t("expectedDeliveryDate")}
              type="date"
              value={expectedDeliveryDate}
              onChange={(e) => setExpectedDeliveryDate(e.target.value)}
            />
            <div className="sm:col-span-2 lg:col-span-4">
              <TextAreaField label={t("notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title={t("lineItems")} />
          <div className="flex flex-col gap-3">
            {lines.map((line) => (
              <div key={line.key} className="grid grid-cols-1 gap-3 rounded-md border border-border p-3 sm:grid-cols-6">
                <div className="sm:col-span-2">
                  <SelectField
                    label={t("material")}
                    value={line.materialId}
                    onChange={(e) => updateLine(line.key, { materialId: e.target.value })}
                  >
                    <option value="">{t("noMaterialOption")}</option>
                    {materials.map((m) => (
                      <option key={m.id} value={m.id}>
                        {brandName(m.brand_id)} — {m.name}
                      </option>
                    ))}
                  </SelectField>
                </div>
                <div className="sm:col-span-2">
                  <TextField
                    label={t("description")}
                    value={line.description}
                    onChange={(e) => updateLine(line.key, { description: e.target.value })}
                    required
                  />
                </div>
                <TextField
                  label={t("quantity")}
                  type="number"
                  min="0"
                  step="0.001"
                  value={line.quantity}
                  onChange={(e) => updateLine(line.key, { quantity: e.target.value })}
                  required
                />
                <TextField label={t("unit")} value={line.unit} onChange={(e) => updateLine(line.key, { unit: e.target.value })} />
                <TextField
                  label={t("unitCost")}
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.unitCost}
                  onChange={(e) => updateLine(line.key, { unitCost: e.target.value })}
                />
                <div className="flex items-end sm:col-span-6">
                  <Button type="button" variant="secondary" onClick={() => removeLine(line.key)} disabled={lines.length === 1}>
                    {t("removeLine")}
                  </Button>
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between">
              <Button type="button" variant="secondary" onClick={addLine}>
                {t("addLine")}
              </Button>
              <p className="text-sm font-medium text-text-primary">
                {t("estimatedTotal")}: {currency} {total.toFixed(2)}
              </p>
            </div>
          </div>
        </Card>

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="flex justify-end">
          <Button type="submit" loading={submitting} disabled={!supplierId}>
            {t("createOrder")}
          </Button>
        </div>
      </form>
    </div>
  );
}
