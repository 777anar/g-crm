"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Columns3 } from "lucide-react";
import { useLocalStorageState } from "@/lib/use-local-storage-state";
import { useCloseOnEscape, useOutsideClick } from "@/lib/use-outside-click";

/** Shared class string for a sticky, scrollable table wrapper -- one
 * definition instead of every list page hand-rolling the same overflow/
 * sticky-header incantation (UI_UX_GUIDELINES.md section 5.4: "sticky
 * header row"). Use together with `stickyTheadClass` on the <thead>. */
export const tableScrollShellClass = "overflow-auto rounded-lg border border-border bg-surface max-h-[70vh]";
export const stickyTheadClass = "sticky top-0 z-10 border-b border-border bg-bg text-text-secondary";

// ── Column visibility ────────────────────────────────────────────────────────

export type ColumnDef = { id: string; label: string };

export function useColumnVisibility(tableId: string, columns: ColumnDef[]) {
  const [hidden, setHidden] = useLocalStorageState<string[]>(`g_erp_table_hidden_cols:${tableId}`, []);
  const hiddenSet = new Set(hidden);

  function isVisible(id: string) {
    return !hiddenSet.has(id);
  }

  function toggle(id: string) {
    setHidden(hiddenSet.has(id) ? hidden.filter((h) => h !== id) : [...hidden, id]);
  }

  function reset() {
    setHidden([]);
  }

  return { isVisible, toggle, reset, hiddenCount: hidden.length, columns };
}

export function ColumnVisibilityMenu({
  columns,
  isVisible,
  toggle,
  reset,
}: {
  columns: ColumnDef[];
  isVisible: (id: string) => boolean;
  toggle: (id: string) => void;
  reset: () => void;
}) {
  const t = useTranslations("common");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  useOutsideClick(containerRef, () => setOpen(false));
  useCloseOnEscape(open, () => setOpen(false));

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t("columns")}
        aria-expanded={open}
        className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-text-primary hover:bg-bg"
      >
        <Columns3 size={13} strokeWidth={1.2} aria-hidden />
        {t("columns")}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 w-52 rounded-md border border-border bg-surface py-1 shadow-elevated">
          <p className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-text-secondary">{t("columns")}</p>
          <ul className="max-h-64 overflow-y-auto">
            {columns.map((col) => (
              <li key={col.id}>
                <label className="flex items-center gap-2 px-3 py-1.5 text-sm text-text-primary hover:bg-bg">
                  <input
                    type="checkbox"
                    checked={isVisible(col.id)}
                    onChange={() => toggle(col.id)}
                    className="rounded border-border"
                  />
                  {col.label}
                </label>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={reset}
            className="mt-1 w-full border-t border-border px-3 py-1.5 text-left text-xs text-primary hover:bg-bg"
          >
            {t("resetColumns")}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Column resize ────────────────────────────────────────────────────────────

const MIN_COLUMN_WIDTH = 72;

export function useResizableColumns(tableId: string, defaultWidths: Record<string, number>) {
  const [widths, setWidths] = useLocalStorageState<Record<string, number>>(
    `g_erp_table_col_widths:${tableId}`,
    defaultWidths
  );
  const dragState = useRef<{ id: string; startX: number; startWidth: number } | null>(null);

  function widthOf(id: string): number {
    return widths[id] ?? defaultWidths[id] ?? 140;
  }

  function startResize(id: string) {
    return (e: React.MouseEvent) => {
      e.preventDefault();
      dragState.current = { id, startX: e.clientX, startWidth: widthOf(id) };

      function onMouseMove(moveEvent: MouseEvent) {
        if (!dragState.current) return;
        const delta = moveEvent.clientX - dragState.current.startX;
        const next = Math.max(MIN_COLUMN_WIDTH, dragState.current.startWidth + delta);
        setWidths({ ...widths, [dragState.current.id]: next });
      }
      function onMouseUp() {
        dragState.current = null;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      }
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    };
  }

  return { widthOf, startResize };
}

/** Drop inside a <th className="relative"> as the last child. Purely a
 * visual/pointer affordance -- table semantics stay on the real <th>. */
export function ColumnResizeHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <span
      onMouseDown={onMouseDown}
      className="absolute right-0 top-0 h-full w-1.5 cursor-col-resize select-none hover:bg-primary/40"
      aria-hidden
    />
  );
}

// ── Saved filters ────────────────────────────────────────────────────────────

export type SavedFilterPreset<T> = { name: string; filters: T };

export function useSavedFilters<T>(tableId: string) {
  const [presets, setPresets] = useLocalStorageState<SavedFilterPreset<T>[]>(
    `g_erp_saved_filters:${tableId}`,
    []
  );

  function save(name: string, filters: T) {
    const trimmed = name.trim();
    if (!trimmed) return;
    setPresets([...presets.filter((p) => p.name !== trimmed), { name: trimmed, filters }]);
  }

  function remove(name: string) {
    setPresets(presets.filter((p) => p.name !== name));
  }

  return { presets, save, remove };
}

export function SavedFiltersBar<T>({
  presets,
  onApply,
  onSave,
  onRemove,
}: {
  presets: SavedFilterPreset<T>[];
  onApply: (filters: T) => void;
  onSave: (name: string) => void;
  onRemove: (name: string) => void;
}) {
  const t = useTranslations("common");
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");

  function handleSave() {
    if (!name.trim()) return;
    onSave(name.trim());
    setName("");
    setNaming(false);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {presets.map((preset) => (
        <span
          key={preset.name}
          className="flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1 text-xs text-text-primary"
        >
          <button type="button" onClick={() => onApply(preset.filters)} className="hover:text-primary">
            {preset.name}
          </button>
          <button
            type="button"
            onClick={() => onRemove(preset.name)}
            aria-label={t("deleteSavedFilter", { name: preset.name })}
            className="text-text-secondary hover:text-danger"
          >
            ✕
          </button>
        </span>
      ))}

      {naming ? (
        <span className="flex items-center gap-1">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSave();
              if (e.key === "Escape") setNaming(false);
            }}
            placeholder={t("filterNamePlaceholder")}
            className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
          />
          <button type="button" onClick={handleSave} className="text-xs font-medium text-primary hover:underline">
            {t("save")}
          </button>
        </span>
      ) : (
        <button
          type="button"
          onClick={() => setNaming(true)}
          className="rounded-full border border-dashed border-border px-2.5 py-1 text-xs text-text-secondary hover:border-primary hover:text-primary"
        >
          + {t("saveCurrentFilters")}
        </button>
      )}
    </div>
  );
}
