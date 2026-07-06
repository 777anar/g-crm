"use client";

/** A clickable <th> that toggles a "field" / "-field" sort string, with a
 * visible direction indicator -- used by Customers and Leads list tables.
 * `width`/`resizeHandle` are optional additions for pages that opt into the
 * column-resize toolkit (components/ui/data-table.tsx); omitting them keeps
 * every existing caller's behavior unchanged. */
export function SortableHeader({
  field,
  label,
  sort,
  onSortChange,
  width,
  resizeHandle,
}: {
  field: string;
  label: string;
  sort: string;
  onSortChange: (next: string) => void;
  width?: number;
  resizeHandle?: React.ReactNode;
}) {
  const active = sort.replace(/^-/, "") === field;
  const descending = sort.startsWith("-");

  function handleClick() {
    if (!active) {
      onSortChange(field);
    } else {
      onSortChange(descending ? field : `-${field}`);
    }
  }

  return (
    <th className="relative px-4 py-2 font-medium" style={width ? { width } : undefined}>
      <button
        type="button"
        onClick={handleClick}
        aria-sort={active ? (descending ? "descending" : "ascending") : undefined}
        className="flex items-center gap-1 hover:text-text-primary"
      >
        {label}
        <span className="inline-flex w-3 flex-col leading-none text-[8px] text-text-secondary">
          <span className={active && !descending ? "text-primary" : ""}>▲</span>
          <span className={active && descending ? "text-primary" : ""}>▼</span>
        </span>
      </button>
      {resizeHandle}
    </th>
  );
}
