import { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

function FieldShell({
  label,
  htmlFor,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={htmlFor} className="text-sm font-medium text-text-primary">
        {label}
      </label>
      {children}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}

const inputClasses =
  "rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export function TextField({
  label,
  error,
  id,
  ...props
}: { label: string; error?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldShell label={label} htmlFor={id ?? label} error={error}>
      <input id={id ?? label} className={inputClasses} {...props} />
    </FieldShell>
  );
}

export function TextAreaField({
  label,
  error,
  id,
  ...props
}: { label: string; error?: string } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <FieldShell label={label} htmlFor={id ?? label} error={error}>
      <textarea id={id ?? label} className={inputClasses} rows={3} {...props} />
    </FieldShell>
  );
}

export function SelectField({
  label,
  error,
  id,
  children,
  ...props
}: { label: string; error?: string } & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <FieldShell label={label} htmlFor={id ?? label} error={error}>
      <select id={id ?? label} className={inputClasses} {...props}>
        {children}
      </select>
    </FieldShell>
  );
}
