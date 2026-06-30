"use client";

/** A clickable <th> that toggles a "field" / "-field" sort string, with a
 * visible direction indicator -- used by Customers and Leads list tables. */
export function SortableHeader({
  field,
  label,
  sort,
  onSortChange,
}: {
  field: string;
  label: string;
  sort: string;
  onSortChange: (next: string) => void;
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
    <th className="px-4 py-2 font-medium">
      <button
        type="button"
        onClick={handleClick}
        className="flex items-center gap-1 hover:text-text-primary"
      >
        {label}
        <span className="inline-flex w-3 flex-col leading-none text-[8px] text-text-secondary">
          <span className={active && !descending ? "text-primary" : ""}>▲</span>
          <span className={active && descending ? "text-primary" : ""}>▼</span>
        </span>
      </button>
    </th>
  );
}
