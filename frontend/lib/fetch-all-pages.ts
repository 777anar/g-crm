import type { Paginated } from "./types";

/** Follows a cursor-paginated endpoint to completion so aggregations built
 * on top of it (counts, filters) never silently under-count past a single
 * page's `limit` -- see PROJECT_AUDIT.md B3. `maxPages` is a safety valve
 * against a runaway loop if a backend contract ever regresses to always
 * returning a `next_cursor`, not a real-world cap. */
export async function fetchAllPages<T>(
  fetchPage: (cursor?: string) => Promise<Paginated<T>>,
  { maxPages = 50 }: { maxPages?: number } = {}
): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | undefined;
  for (let page = 0; page < maxPages; page++) {
    const res = await fetchPage(cursor);
    items.push(...res.items);
    if (!res.next_cursor) break;
    cursor = res.next_cursor;
  }
  return items;
}
