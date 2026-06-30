import { Card } from "@/components/ui/card";

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "primary" | "success" | "warning";
}) {
  const valueClass =
    tone === "primary"
      ? "text-primary"
      : tone === "success"
        ? "text-success"
        : tone === "warning"
          ? "text-warning"
          : "text-text-primary";

  return (
    <Card>
      <p className="text-sm font-medium text-text-secondary">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${valueClass}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-text-secondary">{hint}</p>}
    </Card>
  );
}
