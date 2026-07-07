"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

type ConfirmOptions = { title?: string; confirmLabel?: string; cancelLabel?: string };
type PendingConfirm = ConfirmOptions & { message: string; resolve: (value: boolean) => void };

type ConfirmContextValue = (message: string, options?: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

/** Global styled replacement for the browser's native `confirm()` -- used
 * for destructive-action confirmation (archive, delete, ...) so every such
 * prompt looks and behaves consistently across browsers/OSes
 * (RELEASE_CHECKLIST.md M5), instead of falling back to native `confirm()`
 * like a handful of call sites still did. Mounted once at the app root
 * (see app/(app)/layout.tsx), same pattern as `useToast`. */
export function useConfirm(): ConfirmContextValue {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx;
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const tCommon = useTranslations("common");
  const [pending, setPending] = useState<PendingConfirm | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const confirm = useCallback<ConfirmContextValue>((message, options) => {
    return new Promise<boolean>((resolve) => {
      setPending({ message, resolve, ...options });
    });
  }, []);

  const settle = useCallback(
    (value: boolean) => {
      pending?.resolve(value);
      setPending(null);
    },
    [pending]
  );

  const value = useMemo(() => confirm, [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {pending && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) settle(false);
          }}
        >
          <div
            ref={dialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-message"
            onKeyDown={(e) => {
              if (e.key === "Escape") settle(false);
            }}
            className="w-full max-w-sm rounded-lg border border-border bg-surface p-4 shadow-elevated"
          >
            {pending.title && <h2 className="mb-2 text-sm font-semibold text-text-primary">{pending.title}</h2>}
            <p id="confirm-dialog-message" className="text-sm text-text-primary">
              {pending.message}
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" autoFocus onClick={() => settle(false)}>
                {pending.cancelLabel ?? tCommon("cancel")}
              </Button>
              <Button variant="destructive" onClick={() => settle(true)}>
                {pending.confirmLabel ?? tCommon("delete")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}
