"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "destructive";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover disabled:opacity-50",
  secondary: "border border-border bg-surface text-text-primary hover:bg-bg disabled:opacity-50",
  destructive: "border border-danger text-danger hover:bg-danger hover:text-white disabled:opacity-50",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant };

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", className = "", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  );
});
