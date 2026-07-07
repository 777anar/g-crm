"use client";

import { useRef, useState } from "react";
import { useCloseOnEscape, useOutsideClick } from "@/lib/use-outside-click";

/** Shared open/close state + outside-click/Escape dismissal for a header
 * dropdown (Company switcher, Language switcher, ...). Extracted from the
 * near-identical logic those two components each hand-rolled
 * (RELEASE_CHECKLIST.md M4). */
export function useDropdown() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  useOutsideClick(containerRef, () => setOpen(false));
  useCloseOnEscape(open, () => setOpen(false));
  return { open, containerRef, toggle: () => setOpen((v) => !v), close: () => setOpen(false) };
}

export function DropdownPanel({
  align = "left",
  widthClassName = "w-56",
  label,
  children,
}: {
  align?: "left" | "right";
  widthClassName?: string;
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`absolute ${align === "left" ? "left-0" : "right-0"} top-full z-10 mt-1 ${widthClassName} rounded-md border border-border bg-surface py-1 shadow-lg`}
    >
      {label && <p className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-text-secondary">{label}</p>}
      {children}
    </div>
  );
}

export function DropdownItem({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-bg ${
        active ? "font-semibold text-primary" : "text-text-primary"
      }`}
    >
      {children}
      {active && <span aria-hidden>✓</span>}
    </button>
  );
}
