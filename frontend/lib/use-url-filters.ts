"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

type FilterValues = Record<string, string | boolean | undefined>;

/**
 * Two-way sync between a list page's filter state and its URL query string,
 * so a filtered view is bookmarkable/shareable between teammates. Mirrors
 * useLocalStorageState's SSR-safe pattern: the server render and first
 * client render both ignore the URL (avoiding a hydration mismatch on
 * controlled inputs), then a mount-only effect hydrates real state from it.
 *
 * `hydrate` is called once, after mount, with the current URLSearchParams --
 * use it to call each filter's setState. `currentValues` should be the same
 * shape and is written back to the URL (via router.replace, so filter
 * changes don't pollute browser history) whenever it changes, after
 * hydration has applied.
 */
export function useUrlFilters<T extends FilterValues>(hydrate: (params: URLSearchParams) => void, currentValues: T) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    hydrate(searchParams);
    setReady(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const serialized = JSON.stringify(currentValues);
  useEffect(() => {
    if (!ready) return;
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(currentValues)) {
      if (value === undefined || value === "" || value === false) continue;
      params.set(key, String(value));
    }
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, serialized]);
}
