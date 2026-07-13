"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  addMaterialDocument,
  addMaterialImage,
  addMaterialSize,
  addMaterialThickness,
  deleteMaterialSize,
  deleteMaterialThickness,
  getBrand,
  getMaterial,
  listMaterialDocuments,
  listMaterialImages,
  listMaterialSizes,
  listMaterialThicknesses,
  listPriceLists,
  listPricesForMaterial,
  listSlabs,
  updateMaterial,
  uploadMaterialAsset,
} from "@/lib/api/catalog";
import {
  DOCUMENT_TYPES,
  IMAGE_TYPES,
  SUGGESTED_SIZES_MM,
  SUGGESTED_THICKNESSES_MM,
  type Brand,
  type CatalogDocumentType,
  type ImageType,
  type Material,
  type MaterialDocumentAsset,
  type MaterialImage,
  type MaterialSize,
  type MaterialThickness,
  type PriceList,
  type PriceListEntry,
  type Slab,
} from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EntityStatusBadge, SlabStatusBadge } from "@/components/ui/badge";
import { SelectField, TextField } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocumentTypeLabel, useImageTypeLabel } from "@/lib/i18n/hooks";

export default function MaterialDetailPage() {
  const params = useParams<{ id: string }>();
  const materialId = params.id;
  const t = useTranslations("catalog");
  const tDetail = useTranslations("catalog.materialDetail");
  const tCommon = useTranslations("common");
  const imageTypeLabel = useImageTypeLabel();
  const documentTypeLabel = useDocumentTypeLabel();

  const [material, setMaterial] = useState<Material | null>(null);
  const [brand, setBrand] = useState<Brand | null>(null);
  const [images, setImages] = useState<MaterialImage[]>([]);
  const [documents, setDocuments] = useState<MaterialDocumentAsset[]>([]);
  const [slabs, setSlabs] = useState<Slab[]>([]);
  const [prices, setPrices] = useState<PriceListEntry[]>([]);
  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [thicknesses, setThicknesses] = useState<MaterialThickness[]>([]);
  const [sizes, setSizes] = useState<MaterialSize[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageType, setImageType] = useState<ImageType>("gallery");
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [documentType, setDocumentType] = useState<CatalogDocumentType>("technical_pdf");
  const [newThickness, setNewThickness] = useState("");
  const [newSize, setNewSize] = useState("");

  const reload = useCallback(async () => {
    try {
      const m = await getMaterial(materialId);
      setMaterial(m);
      const [b, imgs, docs, slabRes, priceRes, thicknessRes, sizeRes, priceListRes] = await Promise.all([
        getBrand(m.brand_id),
        listMaterialImages(materialId),
        listMaterialDocuments(materialId),
        listSlabs({ materialId }),
        listPricesForMaterial(materialId),
        listMaterialThicknesses(materialId),
        listMaterialSizes(materialId),
        listPriceLists({ includeHidden: true }),
      ]);
      setBrand(b);
      setImages(imgs.items);
      setDocuments(docs.items);
      setSlabs(slabRes.items);
      setPrices(priceRes.items);
      setThicknesses(thicknessRes.items);
      setSizes(sizeRes.items);
      setPriceLists(priceListRes.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : tDetail("loadFailed"));
    }
  }, [materialId, tDetail]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    try {
      const doc = await uploadMaterialAsset(materialId, file);
      await addMaterialImage(materialId, { document_id: doc.id, image_type: imageType });
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : tDetail("loadFailed"));
    } finally {
      setUploadingImage(false);
      e.target.value = "";
    }
  }

  async function handleDocumentUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingDocument(true);
    try {
      const doc = await uploadMaterialAsset(materialId, file);
      await addMaterialDocument(materialId, { document_id: doc.id, document_type: documentType });
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : tDetail("loadFailed"));
    } finally {
      setUploadingDocument(false);
      e.target.value = "";
    }
  }

  async function handleToggleStatus() {
    if (!material) return;
    const nextStatus = material.status === "active" ? "hidden" : "active";
    try {
      const updated = await updateMaterial(material.id, { status: nextStatus });
      setMaterial(updated);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("updateFailed"));
    }
  }

  async function handleAddThickness(e: React.FormEvent) {
    e.preventDefault();
    if (!newThickness.trim()) return;
    await addMaterialThickness(materialId, { thickness_mm: newThickness.trim(), sort_order: thicknesses.length });
    setNewThickness("");
    await reload();
  }

  async function handleDeleteThickness(id: string) {
    await deleteMaterialThickness(id);
    await reload();
  }

  async function handleAddSize(e: React.FormEvent) {
    e.preventDefault();
    if (!newSize.trim()) return;
    await addMaterialSize(materialId, { dimensions: newSize.trim(), sort_order: sizes.length });
    setNewSize("");
    await reload();
  }

  async function handleDeleteSize(id: string) {
    await deleteMaterialSize(id);
    await reload();
  }

  if (!material && !error) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error && !material) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (!material) return null;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: t("materialsTitle"), href: "/catalog/materials" }, { label: material.name }]} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{material.name}</h1>
          <p className="text-sm text-text-secondary">{brand?.name ?? tCommon("dash")}</p>
        </div>
        <div className="flex items-center gap-2">
          <EntityStatusBadge status={material.status} />
          <Button variant="secondary" onClick={handleToggleStatus}>
            {material.status === "active" ? t("entityStatus.hidden") : t("entityStatus.active")}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <Card>
        <CardHeader title={tDetail("specifications")} />
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Spec label={t("materialType")} value={material.material_type} />
          <Spec label={t("color")} value={material.color} />
          <Spec label={t("finish")} value={material.finish} />
          <Spec label={t("thickness")} value={material.thickness_mm} />
          <Spec label={t("dimensions")} value={material.dimensions} />
          <Spec label={t("countryOfOrigin")} value={material.country_of_origin} />
        </dl>
        {material.description && <p className="mt-3 text-sm text-text-secondary">{material.description}</p>}
      </Card>

      <Card>
        <CardHeader title={tDetail("thicknesses")} />
        {thicknesses.length === 0 ? (
          <p className="text-sm text-text-secondary">{tDetail("noThicknesses")}</p>
        ) : (
          <ul className="mb-3 flex flex-wrap gap-2">
            {thicknesses.map((th) => (
              <li
                key={th.id}
                className="flex items-center gap-2 rounded-md border border-border bg-bg px-3 py-1.5 text-sm text-text-primary"
              >
                {th.thickness_mm} mm
                <button onClick={() => handleDeleteThickness(th.id)} className="text-xs text-danger hover:underline">
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
        <form className="flex items-end gap-2" onSubmit={handleAddThickness}>
          <TextField
            label={tDetail("addThickness")}
            value={newThickness}
            onChange={(e) => setNewThickness(e.target.value)}
            list="thickness-suggestions"
            placeholder={tDetail("thicknessPlaceholder")}
          />
          <datalist id="thickness-suggestions">
            {SUGGESTED_THICKNESSES_MM.map((v) => (
              <option key={v} value={v} />
            ))}
          </datalist>
          <Button type="submit">{tCommon("save")}</Button>
        </form>
      </Card>

      <Card>
        <CardHeader title={tDetail("sizes")} />
        {sizes.length === 0 ? (
          <p className="text-sm text-text-secondary">{tDetail("noSizes")}</p>
        ) : (
          <ul className="mb-3 flex flex-wrap gap-2">
            {sizes.map((sz) => (
              <li
                key={sz.id}
                className="flex items-center gap-2 rounded-md border border-border bg-bg px-3 py-1.5 text-sm text-text-primary"
              >
                {sz.dimensions}
                <button onClick={() => handleDeleteSize(sz.id)} className="text-xs text-danger hover:underline">
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
        <form className="flex items-end gap-2" onSubmit={handleAddSize}>
          <TextField
            label={tDetail("addSize")}
            value={newSize}
            onChange={(e) => setNewSize(e.target.value)}
            list="size-suggestions"
            placeholder={tDetail("sizePlaceholder")}
          />
          <datalist id="size-suggestions">
            {SUGGESTED_SIZES_MM.map((v) => (
              <option key={v} value={v} />
            ))}
          </datalist>
          <Button type="submit">{tCommon("save")}</Button>
        </form>
      </Card>

      <Card>
        <CardHeader title={tDetail("images")} />
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <SelectField
            label={tDetail("imageTypeLabel")}
            value={imageType}
            onChange={(e) => setImageType(e.target.value as ImageType)}
          >
            {IMAGE_TYPES.map((type) => (
              <option key={type} value={type}>
                {imageTypeLabel(type)}
              </option>
            ))}
          </SelectField>
          <label className="inline-flex">
            <span className="sr-only">{tDetail("uploadImage")}</span>
            <input type="file" accept="image/*" onChange={handleImageUpload} disabled={uploadingImage} className="text-sm" />
          </label>
          {uploadingImage && <span className="text-sm text-text-secondary">{tDetail("uploading")}</span>}
        </div>
        {images.length === 0 ? (
          <p className="text-sm text-text-secondary">{tDetail("noImages")}</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {images.map((image) => (
              <li
                key={image.id}
                className="rounded-md border border-border bg-bg px-3 py-2 text-xs text-text-secondary"
              >
                {imageTypeLabel(image.image_type)}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader title={tDetail("documents")} />
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <SelectField
            label={tDetail("documentTypeLabel")}
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value as CatalogDocumentType)}
          >
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {documentTypeLabel(type)}
              </option>
            ))}
          </SelectField>
          <label className="inline-flex">
            <span className="sr-only">{tDetail("uploadDocument")}</span>
            <input type="file" onChange={handleDocumentUpload} disabled={uploadingDocument} className="text-sm" />
          </label>
          {uploadingDocument && <span className="text-sm text-text-secondary">{tDetail("uploading")}</span>}
        </div>
        {documents.length === 0 ? (
          <p className="text-sm text-text-secondary">{tDetail("noDocuments")}</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {documents.map((doc) => (
              <li key={doc.id} className="rounded-md border border-border bg-bg px-3 py-2 text-xs text-text-secondary">
                {documentTypeLabel(doc.document_type)}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader title={tDetail("prices")} />
        {prices.length === 0 ? (
          <p className="text-sm text-text-secondary">{tDetail("noPrices")}</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-text-secondary">
              <tr>
                <th className="py-1.5 font-medium">{tDetail("priceList")}</th>
                <th className="py-1.5 font-medium">{t("costPrice")}</th>
                <th className="py-1.5 font-medium">{t("salePrice")}</th>
              </tr>
            </thead>
            <tbody>
              {prices.map((entry) => {
                const priceList = priceLists.find((pl) => pl.id === entry.price_list_id);
                return (
                  <tr key={entry.id} className="border-b border-border last:border-0">
                    <td className="py-1.5 text-text-secondary">
                      {priceList ? `${priceList.name} (${priceList.currency})` : tCommon("loading")}
                    </td>
                    <td className="py-1.5 text-text-primary">{entry.cost_price}</td>
                    <td className="py-1.5 text-text-primary">{entry.sale_price}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title={tDetail("slabs")} />
        {slabs.length === 0 ? (
          <p className="text-sm text-text-secondary">{tDetail("noSlabs")}</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-text-secondary">
              <tr>
                <th className="py-1.5 font-medium">{t("tableSlabNumber")}</th>
                <th className="py-1.5 font-medium">{t("tableArea")}</th>
                <th className="py-1.5 font-medium">{t("tableStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {slabs.map((slab) => (
                <tr key={slab.id} className="border-b border-border last:border-0">
                  <td className="py-1.5 font-medium text-text-primary">{slab.slab_number}</td>
                  <td className="py-1.5 text-text-secondary">{slab.area_m2 ?? tCommon("dash")}</td>
                  <td className="py-1.5">
                    <SlabStatusBadge status={slab.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function Spec({ label, value }: { label: string; value: string | null }) {
  const tCommon = useTranslations("common");
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-text-secondary">{label}</dt>
      <dd className="text-sm text-text-primary">{value ?? tCommon("dash")}</dd>
    </div>
  );
}
