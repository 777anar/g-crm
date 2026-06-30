import { useEffect, type RefObject } from "react";

export function useOutsideClick(ref: RefObject<HTMLElement | null>, onOutsideClick: () => void): void {
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onOutsideClick();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [ref, onOutsideClick]);
}

/** Closes an open dropdown/menu on Escape -- a keyboard user shouldn't need
 * a mouse to dismiss it. Only attaches the listener while `open` is true. */
export function useCloseOnEscape(open: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);
}
