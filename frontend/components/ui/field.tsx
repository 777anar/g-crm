import { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

function FieldShell({
  label,
  htmlFor,
  error,
  errorId,
  hint,
  required,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  errorId: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={htmlFor} className="text-sm font-medium text-text-primary">
        {label}
        {required && (
          <span className="ml-0.5 text-danger" aria-hidden>
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-text-secondary">{hint}</p>}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

const baseInputClasses =
  "rounded-md border bg-surface px-3 py-2 text-sm text-text-primary transition-colors focus:outline focus:outline-2 focus:outline-offset-1 disabled:cursor-not-allowed disabled:opacity-60";

function inputClasses(hasError?: string) {
  return `${baseInputClasses} ${hasError ? "border-danger focus:outline-danger" : "border-border focus:outline-primary"}`;
}

type CommonFieldProps = { label: string; error?: string; hint?: string; required?: boolean };

export function TextField({
  label,
  error,
  hint,
  required,
  id,
  ...props
}: CommonFieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const fieldId = id ?? label;
  const errorId = `${fieldId}-error`;
  return (
    <FieldShell label={label} htmlFor={fieldId} error={error} errorId={errorId} hint={hint} required={required}>
      <input
        id={fieldId}
        className={inputClasses(error)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        required={required}
        {...props}
      />
    </FieldShell>
  );
}

export function TextAreaField({
  label,
  error,
  hint,
  required,
  id,
  ...props
}: CommonFieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const fieldId = id ?? label;
  const errorId = `${fieldId}-error`;
  return (
    <FieldShell label={label} htmlFor={fieldId} error={error} errorId={errorId} hint={hint} required={required}>
      <textarea
        id={fieldId}
        className={inputClasses(error)}
        rows={3}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        required={required}
        {...props}
      />
    </FieldShell>
  );
}

export function SelectField({
  label,
  error,
  hint,
  required,
  id,
  children,
  ...props
}: CommonFieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
  const fieldId = id ?? label;
  const errorId = `${fieldId}-error`;
  return (
    <FieldShell label={label} htmlFor={fieldId} error={error} errorId={errorId} hint={hint} required={required}>
      <select
        id={fieldId}
        className={inputClasses(error)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        required={required}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  );
}
