import { useEffect, useState } from "react";

/** Persisted client state backed by localStorage -- used for per-table
 * column visibility/widths and saved filter presets so they survive a
 * reload without needing a backend preferences endpoint. Reads lazily on
 * mount (SSR-safe: server and first client render both use `initial`). */
export function useLocalStorageState<T>(key: string, initial: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(initial);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(key);
      if (stored !== null) setValue(JSON.parse(stored));
    } catch {
      // Corrupt/unavailable storage -- fall back to `initial` silently.
    }
  }, [key]);

  function update(next: T) {
    setValue(next);
    try {
      window.localStorage.setItem(key, JSON.stringify(next));
    } catch {
      // Storage full/unavailable (e.g. private browsing) -- state still
      // updates in memory for the current session.
    }
  }

  return [value, update];
}
