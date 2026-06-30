import { useEffect, useState } from "react";

/** Debounces a fast-changing value (e.g. a search input) so dependent
 * effects (e.g. an API call) don't fire on every keystroke. */
export function useDebouncedValue<T>(value: T, delayMs: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
