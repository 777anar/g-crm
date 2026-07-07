"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";

type ToastTone = "success" | "error";
type ToastItem = { id: number; tone: ToastTone; message: string };

type ToastContextValue = {
  success: (message: string) => void;
  error: (message: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

/** Global success/error confirmation toasts -- transient, auto-dismissing,
 * non-blocking, per UI_UX_GUIDELINES.md section 5.7. Mounted once at the
 * app root (see app/(app)/layout.tsx) so any page can call useToast()
 * without wiring its own notification state. */
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

const TONE_CLASSES: Record<ToastTone, string> = {
  success: "border-success/30 bg-surface text-text-primary",
  error: "border-danger/30 bg-surface text-text-primary",
};

const TONE_ICON: Record<ToastTone, string> = {
  success: "✓",
  error: "✕",
};

const TONE_ICON_CLASSES: Record<ToastTone, string> = {
  success: "text-success",
  error: "text-danger",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const tCommon = useTranslations("common");
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (tone: ToastTone, message: string) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, tone, message }]);
      window.setTimeout(() => dismiss(id), 4000);
    },
    [dismiss]
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      success: (message: string) => push("success", message),
      error: (message: string) => push("error", message),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="print-hidden pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 sm:items-end sm:px-6"
        role="status"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex w-full max-w-sm items-start gap-2 rounded-md border px-3 py-2 text-sm shadow-elevated ${TONE_CLASSES[toast.tone]}`}
          >
            <span className={`mt-0.5 font-bold ${TONE_ICON_CLASSES[toast.tone]}`} aria-hidden>
              {TONE_ICON[toast.tone]}
            </span>
            <span className="flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              aria-label={tCommon("dismiss")}
              className="text-text-secondary hover:text-text-primary"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
