"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  getProject,
  listQuotes,
  createQuote,
  listRooms,
  createRoom,
  deleteRoom,
  listProjectItems,
  createProjectItem,
  updateProjectItem,
  deleteProjectItem,
  listProjectItemMeasurements,
  createProjectItemMeasurement,
  updateProjectItemMeasurement,
  deleteProjectItemMeasurement,
  listProjectItemDrawings,
  addProjectItemDrawing,
  deleteProjectItemDrawing,
  listProjectItemPhotos,
  addProjectItemPhoto,
  deleteProjectItemPhoto,
  uploadProjectItemAsset,
} from "@/lib/api/sales";
import {
  getMaterial,
  listBrands,
  listMaterials,
  listMaterialSizes,
  listMaterialThicknesses,
} from "@/lib/api/catalog";
import type {
  Brand,
  Material,
  MaterialSize,
  MaterialThickness,
  Project,
  ProjectItem,
  ProjectItemDrawing,
  ProjectItemMeasurement,
  ProjectItemPhoto,
  Quote,
  Room,
} from "@/lib/types";
import { COMPLETION_STATUSES, PROJECT_ITEM_TYPES, PROJECT_ROOM_TYPES } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField, TextAreaField } from "@/components/ui/field";
import { ProjectStatusBadge, QuoteStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { ApiRequestError } from "@/lib/api-client";
import { usePermission } from "@/lib/permissions";

const PROD_STATUSES = ["pending", "queued", "cutting", "polishing", "quality_check", "done"];
const INST_STATUSES = ["pending", "scheduled", "en_route", "in_progress", "done"];

// Ümumi / Məkanlar / Məmulatlar / Materiallar / Ölçülər / Çertyojlar / Fotolar / İstehsal / Quraşdırma / Təhvil
type Tab =
  | "overview"
  | "rooms"
  | "items"
  | "materials"
  | "measurements"
  | "drawings"
  | "photos"
  | "production"
  | "installation"
  | "handover";

const inputClasses =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("sales");
  const tOrders = useTranslations("orders");
  const tCatalog = useTranslations("catalog");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const router = useRouter();
  const confirm = useConfirm();
  const toast = useToast();
  const canWrite = usePermission("sales:projects:write");

  const [tab, setTab] = useState<Tab>("overview");

  const [project, setProject] = useState<Project | null>(null);
  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [creatingQuote, setCreatingQuote] = useState(false);

  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [itemsByRoom, setItemsByRoom] = useState<Record<string, ProjectItem[]>>({});
  const allItems = Object.values(itemsByRoom).flat();

  const [brands, setBrands] = useState<Brand[]>([]);
  const [stoneSearchResults, setStoneSearchResults] = useState<Material[]>([]);
  const [thicknessOptions, setThicknessOptions] = useState<MaterialThickness[]>([]);
  const [sizeOptions, setSizeOptions] = useState<MaterialSize[]>([]);

  const [materialsById, setMaterialsById] = useState<Record<string, Material>>({});
  const [thicknessesByMaterial, setThicknessesByMaterial] = useState<Record<string, MaterialThickness[]>>({});
  const [sizesByMaterial, setSizesByMaterial] = useState<Record<string, MaterialSize[]>>({});
  const [measurementsByItem, setMeasurementsByItem] = useState<Record<string, ProjectItemMeasurement[]>>({});
  const [drawingsByItem, setDrawingsByItem] = useState<Record<string, ProjectItemDrawing[]>>({});
  const [photosByItem, setPhotosByItem] = useState<Record<string, ProjectItemPhoto[]>>({});
  const [rollupLoaded, setRollupLoaded] = useState<Record<string, boolean>>({});

  const [addingRoom, setAddingRoom] = useState(false);
  const [newRoomType, setNewRoomType] = useState<string>("kitchen");
  const [newRoomName, setNewRoomName] = useState("");

  const [addingItemToRoom, setAddingItemToRoom] = useState<string | null>(null);
  const [newItemType, setNewItemType] = useState<string>("countertop");
  const [newItemName, setNewItemName] = useState("");
  const [newItemBrandId, setNewItemBrandId] = useState("");
  const [newItemStoneSearch, setNewItemStoneSearch] = useState("");
  const [newItemMaterialId, setNewItemMaterialId] = useState("");
  const [newItemThicknessId, setNewItemThicknessId] = useState("");
  const [newItemSizeId, setNewItemSizeId] = useState("");
  const [newItemQuantity, setNewItemQuantity] = useState("1");
  const [newItemNotes, setNewItemNotes] = useState("");
  const debouncedStoneSearch = useDebouncedValue(newItemStoneSearch, 300);

  const [expandedItemId, setExpandedItemId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const [proj, qs] = await Promise.all([getProject(id), listQuotes(id)]);
    setProject(proj);
    setQuotes(qs.items);
  }, [id]);

  useEffect(() => {
    reload().finally(() => setLoading(false));
  }, [reload]);

  const loadRoomsAndItems = useCallback(async () => {
    const roomsRes = await listRooms(id);
    setRooms(roomsRes.items);
    const entries = await Promise.all(
      roomsRes.items.map(async (r) => [r.id, (await listProjectItems(r.id)).items] as const)
    );
    setItemsByRoom(Object.fromEntries(entries));
  }, [id]);

  useEffect(() => {
    if (tab !== "overview" && rooms === null) {
      loadRoomsAndItems().catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    }
  }, [tab, rooms, loadRoomsAndItems, t]);

  useEffect(() => {
    if (
      (tab === "measurements" || tab === "drawings" || tab === "photos") &&
      allItems.length > 0 &&
      !rollupLoaded[tab]
    ) {
      (async () => {
        if (tab === "measurements") {
          const entries = await Promise.all(
            allItems.map(async (i) => [i.id, (await listProjectItemMeasurements(i.id)).items] as const)
          );
          setMeasurementsByItem((prev) => ({ ...prev, ...Object.fromEntries(entries) }));
        } else if (tab === "drawings") {
          const entries = await Promise.all(
            allItems.map(async (i) => [i.id, (await listProjectItemDrawings(i.id)).items] as const)
          );
          setDrawingsByItem((prev) => ({ ...prev, ...Object.fromEntries(entries) }));
        } else if (tab === "photos") {
          const entries = await Promise.all(
            allItems.map(async (i) => [i.id, (await listProjectItemPhotos(i.id)).items] as const)
          );
          setPhotosByItem((prev) => ({ ...prev, ...Object.fromEntries(entries) }));
        }
        setRollupLoaded((prev) => ({ ...prev, [tab]: true }));
      })();
    }
  }, [tab, allItems, rollupLoaded]);

  useEffect(() => {
    if (addingItemToRoom) {
      listBrands().then((res) => setBrands(res.items));
    }
  }, [addingItemToRoom]);

  // Searchable Stone selector: server-side search scoped to the chosen
  // Brand, debounced so it doesn't fire on every keystroke.
  useEffect(() => {
    if (!newItemBrandId) {
      setStoneSearchResults([]);
      return;
    }
    listMaterials({ brandId: newItemBrandId, search: debouncedStoneSearch || undefined, limit: 20 }).then((res) =>
      setStoneSearchResults(res.items)
    );
  }, [newItemBrandId, debouncedStoneSearch]);

  // Thickness/Size options depend on the selected Stone.
  useEffect(() => {
    if (!newItemMaterialId) {
      setThicknessOptions([]);
      setSizeOptions([]);
      return;
    }
    Promise.all([listMaterialThicknesses(newItemMaterialId), listMaterialSizes(newItemMaterialId)]).then(
      ([thicknessRes, sizeRes]) => {
        setThicknessOptions(thicknessRes.items);
        setSizeOptions(sizeRes.items);
      }
    );
  }, [newItemMaterialId]);

  useEffect(() => {
    const missing = Array.from(
      new Set(allItems.map((i) => i.material_id).filter((id): id is string => !!id && !materialsById[id]))
    );
    if (missing.length === 0) return;
    Promise.all(missing.map((materialId) => getMaterial(materialId))).then((materials) => {
      setMaterialsById((prev) => {
        const next = { ...prev };
        materials.forEach((m) => { next[m.id] = m; });
        return next;
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allItems]);

  // Resolve the specific Thickness/Size chosen per item (not just the
  // Stone's legacy single thickness_mm/dimensions) for display.
  useEffect(() => {
    const materialIds = Array.from(
      new Set(
        allItems
          .filter((i) => i.material_thickness_id || i.material_size_id)
          .map((i) => i.material_id)
          .filter((id): id is string => !!id && !thicknessesByMaterial[id])
      )
    );
    if (materialIds.length === 0) return;
    Promise.all(
      materialIds.map((materialId) =>
        Promise.all([listMaterialThicknesses(materialId), listMaterialSizes(materialId)]).then(
          ([thicknessRes, sizeRes]) => [materialId, thicknessRes.items, sizeRes.items] as const
        )
      )
    ).then((results) => {
      setThicknessesByMaterial((prev) => {
        const next = { ...prev };
        results.forEach(([materialId, items]) => { next[materialId] = items; });
        return next;
      });
      setSizesByMaterial((prev) => {
        const next = { ...prev };
        results.forEach(([materialId, , items]) => { next[materialId] = items; });
        return next;
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allItems]);

  async function handleNewQuote() {
    setCreatingQuote(true);
    try {
      const q = await createQuote(id);
      router.push(`/sales/projects/${id}/quotes/${q.id}`);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setCreatingQuote(false);
    }
  }

  async function handleCreateRoom(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createRoom(id, { room_type: newRoomType, name: newRoomName || undefined });
      setAddingRoom(false);
      setNewRoomName("");
      await loadRoomsAndItems();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleDeleteRoom(roomId: string) {
    if (!(await confirm(tCommon("confirmDelete")))) return;
    try {
      await deleteRoom(roomId);
      await loadRoomsAndItems();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleCreateItem(e: React.FormEvent, roomId: string) {
    e.preventDefault();
    try {
      await createProjectItem(roomId, {
        item_type: newItemType,
        name: newItemName || undefined,
        material_id: newItemMaterialId || undefined,
        material_thickness_id: newItemThicknessId || undefined,
        material_size_id: newItemSizeId || undefined,
        quantity: newItemQuantity,
        notes: newItemNotes || undefined,
      });
      setAddingItemToRoom(null);
      setNewItemName("");
      setNewItemBrandId("");
      setNewItemStoneSearch("");
      setNewItemMaterialId("");
      setNewItemThicknessId("");
      setNewItemSizeId("");
      setNewItemQuantity("1");
      setNewItemNotes("");
      await loadRoomsAndItems();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleDeleteItem(itemId: string) {
    if (!(await confirm(tCommon("confirmDelete")))) return;
    try {
      await deleteProjectItem(itemId);
      await loadRoomsAndItems();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleItemStatusChange(
    itemId: string,
    field: "production_status" | "installation_status" | "completion_status",
    value: string
  ) {
    try {
      await updateProjectItem(itemId, { [field]: value });
      await loadRoomsAndItems();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  function roomLabel(room: Room) {
    const typeLabel = t(`roomType_${room.room_type}` as Parameters<typeof t>[0]);
    return room.name ? `${typeLabel} — ${room.name}` : typeLabel;
  }

  function roomLabelForItem(item: ProjectItem) {
    const room = (rooms || []).find((r) => r.id === item.room_id);
    return room ? roomLabel(room) : tCommon("dash");
  }

  function itemLabel(item: ProjectItem) {
    const typeLabel = t(`itemType_${item.item_type}` as Parameters<typeof t>[0]);
    return item.name ? `${typeLabel} — ${item.name}` : typeLabel;
  }

  function materialLabel(item: ProjectItem) {
    if (!item.material_id) return tCommon("dash");
    const material = materialsById[item.material_id];
    if (!material) return tCommon("loading");

    // Prefer the specific Thickness/Size chosen for this item (Sprint 4's
    // normalized options); fall back to the Stone's legacy single
    // thickness_mm/dimensions fields for items created before this sprint.
    const thickness = item.material_thickness_id
      ? thicknessesByMaterial[item.material_id]?.find((th) => th.id === item.material_thickness_id)?.thickness_mm
      : material.thickness_mm;
    const size = item.material_size_id
      ? sizesByMaterial[item.material_id]?.find((sz) => sz.id === item.material_size_id)?.dimensions
      : material.dimensions;

    return `${material.name} — ${thickness ?? tCommon("dash")}mm — ${size ?? tCommon("dash")}`;
  }

  function groupItemsByMaterial(items: ProjectItem[]) {
    const groups = new Map<string, ProjectItem[]>();
    for (const item of items) {
      if (!item.material_id) continue;
      const key = `${item.material_id}|${item.material_thickness_id ?? ""}|${item.material_size_id ?? ""}`;
      const existing = groups.get(key);
      if (existing) existing.push(item);
      else groups.set(key, [item]);
    }
    return Array.from(groups.entries()).map(([key, groupItems]) => ({ key, items: groupItems }));
  }

  if (loading) return <TableSkeleton rows={5} columns={5} />;
  if (!project) return <p className="text-sm text-text-secondary">{tCommon("notFound")}</p>;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("projects"), href: "/sales/projects" }, { label: project.name }]} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{project.name}</h1>
          <p className="text-sm text-text-secondary">
            {t(`projectType_${project.project_type || "other"}` as Parameters<typeof t>[0])}
            {project.address ? ` · ${project.address}` : ""}
          </p>
        </div>
        <ProjectStatusBadge status={project.status} />
      </div>

      <div className="flex flex-wrap gap-1 border-b border-border pb-2">
        {(
          [
            "overview",
            "rooms",
            "items",
            "materials",
            "measurements",
            "drawings",
            "photos",
            "production",
            "installation",
            "handover",
          ] as Tab[]
        ).map(
          (key) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                tab === key ? "bg-primary text-white" : "text-text-secondary hover:bg-bg"
              }`}
            >
              {t(`tab${key.charAt(0).toUpperCase()}${key.slice(1)}` as Parameters<typeof t>[0])}
            </button>
          )
        )}
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {tab === "overview" && (
        <div className="flex flex-col gap-4">
          {canWrite && (
            <div className="flex justify-end">
              <Button onClick={handleNewQuote} disabled={creatingQuote}>
                {creatingQuote ? t("creating") : t("createQuote")}
              </Button>
            </div>
          )}

          <h2 className="text-lg font-semibold text-text-primary">{t("quotesTitle")}</h2>
          {quotes === null && <TableSkeleton rows={4} columns={5} />}
          {quotes && quotes.length === 0 && <EmptyState title={t("noQuotesYet")} />}
          {quotes && quotes.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-border bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
                  <tr>
                    <th className="px-4 py-2 font-medium">{t("tableQuoteNum")}</th>
                    <th className="px-4 py-2 font-medium">{t("quoteVersion")}</th>
                    <th className="px-4 py-2 font-medium">{t("quoteStatus")}</th>
                    <th className="px-4 py-2 font-medium">{t("tableTotal")}</th>
                    <th className="px-4 py-2 font-medium">{t("validUntil")}</th>
                    <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                  </tr>
                </thead>
                <tbody>
                  {quotes.map((q) => (
                    <tr
                      key={q.id}
                      onClick={() => router.push(`/sales/projects/${id}/quotes/${q.id}`)}
                      className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                    >
                      <td className="px-4 py-2 font-mono font-medium text-text-primary">{q.quote_number}</td>
                      <td className="px-4 py-2 text-text-secondary">v{q.version}</td>
                      <td className="px-4 py-2">
                        <QuoteStatusBadge status={q.status} />
                      </td>
                      <td className="px-4 py-2 text-text-primary">
                        {q.currency} {parseFloat(q.total_final).toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-text-secondary">
                        {q.valid_until ? formatDate(q.valid_until) : tCommon("dash")}
                      </td>
                      <td className="px-4 py-2 text-text-secondary">{formatDate(q.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "rooms" && (
        <div className="flex flex-col gap-3">
          {canWrite && (
            <div className="flex justify-end">
              <Button onClick={() => setAddingRoom((v) => !v)}>{t("addRoom")}</Button>
            </div>
          )}

          {canWrite && addingRoom && (
            <Card>
              <form className="grid grid-cols-1 gap-3 sm:grid-cols-3" onSubmit={handleCreateRoom}>
                <SelectField label={t("roomType")} value={newRoomType} onChange={(e) => setNewRoomType(e.target.value)}>
                  {PROJECT_ROOM_TYPES.map((rt) => (
                    <option key={rt} value={rt}>
                      {t(`roomType_${rt}` as Parameters<typeof t>[0])}
                    </option>
                  ))}
                </SelectField>
                <TextField label={t("roomName")} value={newRoomName} onChange={(e) => setNewRoomName(e.target.value)} />
                <div className="flex items-end">
                  <Button type="submit">{tCommon("save")}</Button>
                </div>
              </form>
            </Card>
          )}

          {rooms === null && <TableSkeleton rows={3} columns={3} />}
          {rooms && rooms.length === 0 && !addingRoom && <EmptyState title={t("noRoomsYet")} />}

          {rooms &&
            rooms.map((room) => (
              <Card key={room.id}>
                <CardHeader
                  title={roomLabel(room)}
                  action={
                    canWrite && (
                      <div className="flex gap-2">
                        <Button variant="secondary" onClick={() => setAddingItemToRoom(addingItemToRoom === room.id ? null : room.id)}>
                          {t("addProjectItem")}
                        </Button>
                        <button onClick={() => handleDeleteRoom(room.id)} className="text-sm text-danger hover:underline">
                          {tCommon("delete")}
                        </button>
                      </div>
                    )
                  }
                />

                {canWrite && addingItemToRoom === room.id && (
                  <form
                    className="mb-3 grid grid-cols-1 gap-3 rounded-md border border-border bg-bg p-3 sm:grid-cols-3"
                    onSubmit={(e) => handleCreateItem(e, room.id)}
                  >
                    <SelectField label={t("itemType")} value={newItemType} onChange={(e) => setNewItemType(e.target.value)}>
                      {PROJECT_ITEM_TYPES.map((it) => (
                        <option key={it} value={it}>
                          {t(`itemType_${it}` as Parameters<typeof t>[0])}
                        </option>
                      ))}
                    </SelectField>
                    <TextField label={t("itemName")} value={newItemName} onChange={(e) => setNewItemName(e.target.value)} />
                    <TextField
                      label={t("quantity")}
                      type="text"
                      value={newItemQuantity}
                      onChange={(e) => setNewItemQuantity(e.target.value)}
                    />
                    <SelectField
                      label={tCatalog("brand")}
                      value={newItemBrandId}
                      onChange={(e) => {
                        setNewItemBrandId(e.target.value);
                        setNewItemStoneSearch("");
                        setNewItemMaterialId("");
                        setNewItemThicknessId("");
                        setNewItemSizeId("");
                      }}
                    >
                      <option value="">{tCommon("select")}</option>
                      {brands.map((b) => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </SelectField>
                    <TextField
                      label={t("searchStone")}
                      value={newItemStoneSearch}
                      onChange={(e) => setNewItemStoneSearch(e.target.value)}
                      disabled={!newItemBrandId}
                      placeholder={t("searchStonePlaceholder")}
                    />
                    <SelectField
                      label={t("stone")}
                      value={newItemMaterialId}
                      onChange={(e) => {
                        setNewItemMaterialId(e.target.value);
                        setNewItemThicknessId("");
                        setNewItemSizeId("");
                      }}
                      disabled={!newItemBrandId}
                    >
                      <option value="">{tCommon("select")}</option>
                      {stoneSearchResults.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </SelectField>
                    <SelectField
                      label={t("thickness")}
                      value={newItemThicknessId}
                      onChange={(e) => setNewItemThicknessId(e.target.value)}
                      disabled={!newItemMaterialId || thicknessOptions.length === 0}
                    >
                      <option value="">{tCommon("select")}</option>
                      {thicknessOptions.map((th) => (
                        <option key={th.id} value={th.id}>
                          {th.thickness_mm} mm
                        </option>
                      ))}
                    </SelectField>
                    <SelectField
                      label={t("size")}
                      value={newItemSizeId}
                      onChange={(e) => setNewItemSizeId(e.target.value)}
                      disabled={!newItemMaterialId || sizeOptions.length === 0}
                    >
                      <option value="">{tCommon("select")}</option>
                      {sizeOptions.map((sz) => (
                        <option key={sz.id} value={sz.id}>
                          {sz.dimensions}
                        </option>
                      ))}
                    </SelectField>
                    <div className="sm:col-span-3">
                      <TextAreaField label={t("notes")} value={newItemNotes} onChange={(e) => setNewItemNotes(e.target.value)} />
                    </div>
                    <div className="flex items-end sm:col-span-3">
                      <Button type="submit">{tCommon("save")}</Button>
                    </div>
                  </form>
                )}

                {(itemsByRoom[room.id] || []).length === 0 ? (
                  <p className="text-sm text-text-secondary">{t("noProjectItemsYet")}</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {(itemsByRoom[room.id] || []).map((item) => (
                      <ProjectItemRow
                        key={item.id}
                        canWrite={canWrite}
                        item={item}
                        label={itemLabel(item)}
                        materialLabel={materialLabel(item)}
                        expanded={expandedItemId === item.id}
                        onToggle={() => setExpandedItemId(expandedItemId === item.id ? null : item.id)}
                        onDelete={() => handleDeleteItem(item.id)}
                        t={t}
                        measurements={measurementsByItem[item.id]}
                        drawings={drawingsByItem[item.id]}
                        photos={photosByItem[item.id]}
                        onLoadSubResources={async () => {
                          const [m, d, p] = await Promise.all([
                            listProjectItemMeasurements(item.id),
                            listProjectItemDrawings(item.id),
                            listProjectItemPhotos(item.id),
                          ]);
                          setMeasurementsByItem((prev) => ({ ...prev, [item.id]: m.items }));
                          setDrawingsByItem((prev) => ({ ...prev, [item.id]: d.items }));
                          setPhotosByItem((prev) => ({ ...prev, [item.id]: p.items }));
                        }}
                        onAddMeasurement={async (data) => {
                          try {
                            await createProjectItemMeasurement(item.id, data);
                            const m = await listProjectItemMeasurements(item.id);
                            setMeasurementsByItem((prev) => ({ ...prev, [item.id]: m.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                        onAttachSignature={async (measurementId, file) => {
                          try {
                            const doc = await uploadProjectItemAsset(item.id, "project_item_measurement", file);
                            await updateProjectItemMeasurement(measurementId, {
                              status: "final",
                              customer_signature_document_id: doc.id,
                            });
                            const m = await listProjectItemMeasurements(item.id);
                            setMeasurementsByItem((prev) => ({ ...prev, [item.id]: m.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                        onDeleteMeasurement={async (measurementId) => {
                          if (!(await confirm(tCommon("confirmDelete")))) return;
                          try {
                            await deleteProjectItemMeasurement(measurementId);
                            const m = await listProjectItemMeasurements(item.id);
                            setMeasurementsByItem((prev) => ({ ...prev, [item.id]: m.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                        onAddDrawing={async (file, drawingType) => {
                          try {
                            const doc = await uploadProjectItemAsset(item.id, "project_item_drawing", file);
                            await addProjectItemDrawing(item.id, { document_id: doc.id, drawing_type: drawingType });
                            const d = await listProjectItemDrawings(item.id);
                            setDrawingsByItem((prev) => ({ ...prev, [item.id]: d.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                        onDeleteDrawing={async (drawingId) => {
                          if (!(await confirm(tCommon("confirmDelete")))) return;
                          try {
                            await deleteProjectItemDrawing(drawingId);
                            const d = await listProjectItemDrawings(item.id);
                            setDrawingsByItem((prev) => ({ ...prev, [item.id]: d.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                        onAddPhoto={async (file, caption) => {
                          try {
                            const doc = await uploadProjectItemAsset(item.id, "project_item_photo", file);
                            await addProjectItemPhoto(item.id, { document_id: doc.id, caption });
                            const p = await listProjectItemPhotos(item.id);
                            setPhotosByItem((prev) => ({ ...prev, [item.id]: p.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                        onDeletePhoto={async (photoId) => {
                          if (!(await confirm(tCommon("confirmDelete")))) return;
                          try {
                            await deleteProjectItemPhoto(photoId);
                            const p = await listProjectItemPhotos(item.id);
                            setPhotosByItem((prev) => ({ ...prev, [item.id]: p.items }));
                          } catch (err) {
                            toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
                          }
                        }}
                      />
                    ))}
                  </div>
                )}
              </Card>
            ))}
        </div>
      )}

      {tab === "items" && (
        <RollupTable
          items={allItems}
          rooms={rooms}
          emptyLabel={t("noProjectItemsYet")}
          renderRow={(item) => (
            <tr key={item.id} className="border-b border-border last:border-0">
              <td className="px-4 py-2 text-text-secondary">{roomLabelForItem(item)}</td>
              <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
              <td className="px-4 py-2 text-text-secondary">{materialLabel(item)}</td>
              <td className="px-4 py-2 text-text-secondary">{item.quantity} {item.unit}</td>
              <td className="px-4 py-2 text-text-secondary">{item.notes || tCommon("dash")}</td>
            </tr>
          )}
          headers={[t("room"), t("itemType"), t("stone"), t("quantity"), t("notes")]}
        />
      )}

      {tab === "materials" && (
        <MaterialsRollup
          groups={groupItemsByMaterial(allItems)}
          rooms={rooms}
          materialLabel={materialLabel}
          headers={[t("stone"), t("itemCount"), t("totalQuantity")]}
          emptyLabel={t("noMaterialsYet")}
        />
      )}

      {tab === "measurements" && (
        <RollupTable
          items={allItems}
          rooms={rooms}
          emptyLabel={t("noMeasurementsYet")}
          renderRow={(item) =>
            (measurementsByItem[item.id] || []).map((m) => (
              <tr key={m.id} className="border-b border-border last:border-0">
                <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
                <td className="px-4 py-2 text-text-secondary">#{m.revision_number}</td>
                <td className="px-4 py-2 text-text-secondary">{m.length_mm ?? tCommon("dash")}</td>
                <td className="px-4 py-2 text-text-secondary">{m.width_mm ?? tCommon("dash")}</td>
                <td className="px-4 py-2 text-text-secondary">{m.area_m2 ?? tCommon("dash")}</td>
                <td className="px-4 py-2 text-text-secondary">{m.measurer_name || tCommon("dash")}</td>
                <td className="px-4 py-2 text-text-secondary">{m.measured_at ? formatDate(m.measured_at) : tCommon("dash")}</td>
                <td className="px-4 py-2 text-text-secondary">{t(`measurementStatus_${m.status}` as Parameters<typeof t>[0])}</td>
              </tr>
            ))
          }
          headers={[t("itemType"), t("measurementRevision"), t("measurementLength"), t("measurementWidth"), t("measurementArea"), t("measurer"), t("measuredAt"), t("measurementStatus")]}
        />
      )}

      {tab === "drawings" && (
        <RollupTable
          items={allItems}
          rooms={rooms}
          emptyLabel={t("noDrawingsYet")}
          renderRow={(item) =>
            (drawingsByItem[item.id] || []).map((d) => (
              <tr key={d.id} className="border-b border-border last:border-0">
                <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
                <td className="px-4 py-2 text-text-secondary">{t(`drawingType_${d.drawing_type}` as Parameters<typeof t>[0])}</td>
                <td className="px-4 py-2 text-text-secondary">{d.label || tCommon("dash")}</td>
              </tr>
            ))
          }
          headers={[t("itemType"), t("drawingType"), t("drawingLabel")]}
        />
      )}

      {tab === "photos" && (
        <RollupTable
          items={allItems}
          rooms={rooms}
          emptyLabel={t("noPhotosYet")}
          renderRow={(item) =>
            (photosByItem[item.id] || []).map((p) => (
              <tr key={p.id} className="border-b border-border last:border-0">
                <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
                <td className="px-4 py-2 text-text-secondary">{p.caption || tCommon("dash")}</td>
              </tr>
            ))
          }
          headers={[t("itemType"), t("photoCaption")]}
        />
      )}

      {tab === "production" && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("itemType")}</th>
                <th className="px-4 py-2 font-medium">{tOrders("productionStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {allItems.map((item) => (
                <tr key={item.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
                  <td className="px-2 py-1">
                    <select
                      className={inputClasses}
                      value={item.production_status ?? ""}
                      onChange={(e) => handleItemStatusChange(item.id, "production_status", e.target.value)}
                      disabled={!canWrite}
                    >
                      <option value="">—</option>
                      {PROD_STATUSES.map((s) => (
                        <option key={s} value={s}>{tOrders(`prodStatus_${s}` as Parameters<typeof tOrders>[0])}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {allItems.length === 0 && (
                <tr><td colSpan={2} className="px-4 py-4"><EmptyState title={t("noProjectItemsYet")} /></td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "installation" && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("itemType")}</th>
                <th className="px-4 py-2 font-medium">{tOrders("installationStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {allItems.map((item) => (
                <tr key={item.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
                  <td className="px-2 py-1">
                    <select
                      className={inputClasses}
                      value={item.installation_status ?? ""}
                      onChange={(e) => handleItemStatusChange(item.id, "installation_status", e.target.value)}
                      disabled={!canWrite}
                    >
                      <option value="">—</option>
                      {INST_STATUSES.map((s) => (
                        <option key={s} value={s}>{tOrders(`instStatus_${s}` as Parameters<typeof tOrders>[0])}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {allItems.length === 0 && (
                <tr><td colSpan={2} className="px-4 py-4"><EmptyState title={t("noProjectItemsYet")} /></td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "handover" && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <CompletionStat label={t("totalRooms")} value={rooms?.length ?? 0} />
            <CompletionStat label={t("totalProjectItems")} value={allItems.length} />
            <CompletionStat
              label={t("itemsAccepted")}
              value={allItems.filter((i) => i.completion_status === "accepted").length}
            />
          </div>

          <div className="overflow-x-auto rounded-lg border border-border bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-bg text-text-secondary">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("room")}</th>
                  <th className="px-4 py-2 font-medium">{t("itemType")}</th>
                  <th className="px-4 py-2 font-medium">{t("completionStatus")}</th>
                </tr>
              </thead>
              <tbody>
                {allItems.map((item) => (
                  <tr key={item.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 text-text-secondary">{roomLabelForItem(item)}</td>
                    <td className="px-4 py-2 text-text-primary">{itemLabel(item)}</td>
                    <td className="px-2 py-1">
                      <select
                        className={inputClasses}
                        value={item.completion_status ?? ""}
                        onChange={(e) => handleItemStatusChange(item.id, "completion_status", e.target.value)}
                        disabled={!canWrite}
                      >
                        <option value="">—</option>
                        {COMPLETION_STATUSES.map((s) => (
                          <option key={s} value={s}>{t(`completionStatus_${s}` as Parameters<typeof t>[0])}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
                {allItems.length === 0 && (
                  <tr><td colSpan={3} className="px-4 py-4"><EmptyState title={t("noProjectItemsYet")} /></td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function CompletionStat({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase text-text-secondary">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-text-primary">{value}</p>
    </Card>
  );
}

function RollupTable({
  items,
  rooms,
  headers,
  renderRow,
  emptyLabel,
}: {
  items: ProjectItem[];
  rooms: Room[] | null;
  headers: string[];
  renderRow: (item: ProjectItem) => React.ReactNode;
  emptyLabel: string;
}) {
  const rows = items.flatMap((item) => renderRow(item));
  if (rooms === null) return <TableSkeleton rows={3} columns={headers.length} />;
  if (rows.length === 0) return <EmptyState title={emptyLabel} />;
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-bg text-text-secondary">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  );
}

function MaterialsRollup({
  groups,
  rooms,
  materialLabel,
  headers,
  emptyLabel,
}: {
  groups: { key: string; items: ProjectItem[] }[];
  rooms: Room[] | null;
  materialLabel: (item: ProjectItem) => string;
  headers: string[];
  emptyLabel: string;
}) {
  if (rooms === null) return <TableSkeleton rows={3} columns={headers.length} />;
  if (groups.length === 0) return <EmptyState title={emptyLabel} />;
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-bg text-text-secondary">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <tr key={group.key} className="border-b border-border last:border-0">
              <td className="px-4 py-2 text-text-primary">{materialLabel(group.items[0])}</td>
              <td className="px-4 py-2 text-text-secondary">{group.items.length}</td>
              <td className="px-4 py-2 text-text-secondary">
                {group.items.reduce((sum, i) => sum + parseFloat(i.quantity || "0"), 0)} {group.items[0].unit}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProjectItemRow({
  canWrite,
  item,
  label,
  materialLabel,
  expanded,
  onToggle,
  onDelete,
  t,
  measurements,
  drawings,
  photos,
  onLoadSubResources,
  onAddMeasurement,
  onAttachSignature,
  onDeleteMeasurement,
  onAddDrawing,
  onDeleteDrawing,
  onAddPhoto,
  onDeletePhoto,
}: {
  canWrite: boolean;
  item: ProjectItem;
  label: string;
  materialLabel: string;
  expanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  t: ReturnType<typeof useTranslations>;
  measurements?: ProjectItemMeasurement[];
  drawings?: ProjectItemDrawing[];
  photos?: ProjectItemPhoto[];
  onLoadSubResources: () => Promise<void>;
  onAddMeasurement: (data: { length_mm?: string; width_mm?: string; thickness_mm?: string; measurer_name?: string; measured_at?: string; notes?: string }) => Promise<void>;
  onAttachSignature: (measurementId: string, file: File) => Promise<void>;
  onDeleteMeasurement: (measurementId: string) => Promise<void>;
  onAddDrawing: (file: File, drawingType: string) => Promise<void>;
  onDeleteDrawing: (drawingId: string) => Promise<void>;
  onAddPhoto: (file: File, caption: string) => Promise<void>;
  onDeletePhoto: (photoId: string) => Promise<void>;
}) {
  const [length, setLength] = useState("");
  const [width, setWidth] = useState("");
  const [thickness, setThickness] = useState("");
  const [measurer, setMeasurer] = useState("");
  const [measuredAt, setMeasuredAt] = useState("");
  const [drawingType, setDrawingType] = useState("sketch");
  const [photoCaption, setPhotoCaption] = useState("");

  useEffect(() => {
    if (expanded && measurements === undefined) {
      onLoadSubResources();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

  return (
    <div className="rounded-md border border-border">
      <div className="flex items-center justify-between px-3 py-2">
        <button onClick={onToggle} className="flex-1 text-left text-sm font-medium text-text-primary hover:underline">
          {label} {item.material_id && <span className="font-normal text-text-secondary">— {materialLabel}</span>}
        </button>
        <span className="mr-2 text-xs text-text-secondary">{item.quantity} {item.unit}</span>
        {canWrite && (
          <button onClick={onDelete} className="text-xs text-danger hover:underline">✕</button>
        )}
      </div>

      {expanded && (
        <div className="flex flex-col gap-4 border-t border-border p-3">
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase text-text-secondary">{t("tabMeasurements")}</h3>
            {(measurements || []).map((m) => (
              <div key={m.id} className="mb-1 flex items-center justify-between rounded border border-border bg-bg px-2 py-1 text-xs">
                <span>
                  #{m.revision_number} · {m.length_mm ?? "—"}×{m.width_mm ?? "—"}mm · {m.area_m2 ?? "—"}m² ·{" "}
                  {m.measurer_name || "—"} · {t(`measurementStatus_${m.status}` as Parameters<typeof t>[0])}
                  {m.customer_signature_document_id ? ` · ${t("signatureAttached")}` : ""}
                </span>
                <span className="flex items-center gap-2">
                  {canWrite && !m.customer_signature_document_id && (
                    <label className="cursor-pointer text-primary hover:underline">
                      {t("attachSignature")}
                      <input
                        type="file"
                        accept="image/*,application/pdf"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) onAttachSignature(m.id, file);
                          e.target.value = "";
                        }}
                      />
                    </label>
                  )}
                  {canWrite && (
                    <button onClick={() => onDeleteMeasurement(m.id)} className="text-danger hover:underline">✕</button>
                  )}
                </span>
              </div>
            ))}
            {canWrite && (
              <form
                className="mt-2 flex flex-wrap items-end gap-2"
                onSubmit={async (e) => {
                  e.preventDefault();
                  await onAddMeasurement({
                    length_mm: length || undefined,
                    width_mm: width || undefined,
                    thickness_mm: thickness || undefined,
                    measurer_name: measurer || undefined,
                    measured_at: measuredAt || undefined,
                  });
                  setLength("");
                  setWidth("");
                  setThickness("");
                }}
              >
                <input className={inputClasses} placeholder={t("measurementLength")} value={length} onChange={(e) => setLength(e.target.value)} />
                <input className={inputClasses} placeholder={t("measurementWidth")} value={width} onChange={(e) => setWidth(e.target.value)} />
                <input className={inputClasses} placeholder={t("measurementThickness")} value={thickness} onChange={(e) => setThickness(e.target.value)} />
                <input className={inputClasses} placeholder={t("measurer")} value={measurer} onChange={(e) => setMeasurer(e.target.value)} />
                <input className={inputClasses} type="date" value={measuredAt} onChange={(e) => setMeasuredAt(e.target.value)} />
                <Button type="submit">{t("recordMeasurement")}</Button>
              </form>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase text-text-secondary">{t("tabDrawings")}</h3>
            {(drawings || []).map((d) => (
              <div key={d.id} className="mb-1 flex items-center justify-between rounded border border-border bg-bg px-2 py-1 text-xs">
                <span>{t(`drawingType_${d.drawing_type}` as Parameters<typeof t>[0])} · {d.label || "—"}</span>
                {canWrite && (
                  <button onClick={() => onDeleteDrawing(d.id)} className="text-danger hover:underline">✕</button>
                )}
              </div>
            ))}
            {canWrite && (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <select className={inputClasses} value={drawingType} onChange={(e) => setDrawingType(e.target.value)}>
                  {["dwg", "dxf", "sketch", "pdf"].map((dt) => (
                    <option key={dt} value={dt}>{t(`drawingType_${dt}` as Parameters<typeof t>[0])}</option>
                  ))}
                </select>
                <input
                  type="file"
                  className="text-xs"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) onAddDrawing(file, drawingType);
                    e.target.value = "";
                  }}
                />
              </div>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase text-text-secondary">{t("tabPhotos")}</h3>
            {(photos || []).map((p) => (
              <div key={p.id} className="mb-1 flex items-center justify-between rounded border border-border bg-bg px-2 py-1 text-xs">
                <span>{p.caption || "—"}</span>
                {canWrite && (
                  <button onClick={() => onDeletePhoto(p.id)} className="text-danger hover:underline">✕</button>
                )}
              </div>
            ))}
            {canWrite && (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  className={inputClasses}
                  placeholder={t("photoCaption")}
                  value={photoCaption}
                  onChange={(e) => setPhotoCaption(e.target.value)}
                />
                <input
                  type="file"
                  accept="image/*"
                  className="text-xs"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) onAddPhoto(file, photoCaption);
                    e.target.value = "";
                    setPhotoCaption("");
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
