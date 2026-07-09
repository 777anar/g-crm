"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { createMaterial, listBrands, listCollections } from "@/lib/api/catalog";
import { SUGGESTED_MATERIAL_TYPES, type Brand, type Collection } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";

export default function NewMaterialPage() {
  const router = useRouter();
  const t = useTranslations("catalog");
  const tCommon = useTranslations("common");

  const [brands, setBrands] = useState<Brand[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [brandId, setBrandId] = useState("");
  const [collectionId, setCollectionId] = useState("");
  const [name, setName] = useState("");
  const [materialType, setMaterialType] = useState("");
  const [color, setColor] = useState("");
  const [finish, setFinish] = useState("");
  const [countryOfOrigin, setCountryOfOrigin] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listBrands()
      .then((res) => {
        setBrands(res.items);
        if (res.items.length > 0) setBrandId((current) => current || res.items[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!brandId) {
      setCollections([]);
      return;
    }
    listCollections({ brandId }).then((res) => setCollections(res.items)).catch(() => {});
    setCollectionId("");
  }, [brandId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const material = await createMaterial({
        brand_id: brandId,
        collection_id: collectionId || undefined,
        name,
        material_type: materialType || undefined,
        color: color || undefined,
        finish: finish || undefined,
        country_of_origin: countryOfOrigin || undefined,
        description: description || undefined,
      });
      router.push(`/catalog/materials/${material.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader title={t("createMaterial")} subtitle={t("createMaterialHint")} />
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField label={t("brand")} value={brandId} onChange={(e) => setBrandId(e.target.value)} required>
              {brands.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </SelectField>
            <SelectField label={t("collection")} value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
              <option value="">{t("collectionNone")}</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </SelectField>
          </div>

          <TextField label={t("name")} value={name} onChange={(e) => setName(e.target.value)} required autoFocus />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField label={t("materialType")} value={materialType} onChange={(e) => setMaterialType(e.target.value)}>
              <option value="">{tCommon("dash")}</option>
              {SUGGESTED_MATERIAL_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </SelectField>
            <TextField label={t("color")} value={color} onChange={(e) => setColor(e.target.value)} />
            <TextField label={t("finish")} value={finish} onChange={(e) => setFinish(e.target.value)} />
            <TextField
              label={t("countryOfOrigin")}
              value={countryOfOrigin}
              onChange={(e) => setCountryOfOrigin(e.target.value)}
            />
          </div>

          <TextAreaField label={t("description")} value={description} onChange={(e) => setDescription(e.target.value)} />

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => router.back()}>
              {tCommon("cancel")}
            </Button>
            <Button type="submit" disabled={submitting || !name || !brandId}>
              {submitting ? t("creating") : t("createMaterial")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
