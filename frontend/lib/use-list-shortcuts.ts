import { useEffect, type RefObject } from "react";

function isTypingInField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** Keyboard shortcuts shared by every list screen (Customers, Leads):
 * "/" focuses the search box, "c" jumps to the create action, "Escape"
 * blurs whatever's focused (clearing search focus / closing the keyboard's
 * "mode"). Ignored while the user is already typing in a field other than
 * the search box itself, so normal typing (including "c" in a name) is
 * never hijacked. */
export function useListShortcuts({
  searchInputRef,
  onCreate,
}: {
  searchInputRef: RefObject<HTMLInputElement | null>;
  onCreate?: () => void;
}) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "Escape" && document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
        return;
      }

      const typing = isTypingInField(document.activeElement);
      const isSearchBoxFocused = document.activeElement === searchInputRef.current;

      if (e.key === "/" && !typing) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      if (e.key.toLowerCase() === "c" && !typing && !isSearchBoxFocused && onCreate) {
        e.preventDefault();
        onCreate();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [searchInputRef, onCreate]);
}
