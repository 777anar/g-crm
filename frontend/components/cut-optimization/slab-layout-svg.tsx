import type { PlacedPiece } from "@/lib/types";

const COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ec4899", "#06b6d4",
  "#8b5cf6", "#ef4444", "#14b8a6", "#f97316", "#84cc16",
];

function colorForLabel(label: string, index: number): string {
  // Same piece label always gets the same color, regardless of instance
  // index, so multi-quantity pieces read as one visual group on the slab.
  let hash = 0;
  for (let i = 0; i < label.length; i++) hash = (hash * 31 + label.charCodeAt(i)) | 0;
  return COLORS[Math.abs(hash + index) % COLORS.length];
}

/** Renders the slab as an SVG in real millimeter coordinates via viewBox --
 * scales responsively to any container width with zero manual pixel math. */
export function SlabLayoutSvg({
  slabLengthMm,
  slabWidthMm,
  placements,
  className = "",
}: {
  slabLengthMm: number;
  slabWidthMm: number;
  placements: PlacedPiece[];
  className?: string;
}) {
  const labelOrder = Array.from(new Set(placements.map((p) => p.label)));
  const fontSize = Math.max(Math.min(slabLengthMm, slabWidthMm) * 0.035, slabLengthMm * 0.012);

  return (
    <svg
      viewBox={`0 0 ${slabLengthMm} ${slabWidthMm}`}
      className={`w-full rounded-md border border-border bg-bg ${className}`}
      style={{ maxHeight: "70vh" }}
      role="img"
      aria-label="Slab cutting layout"
    >
      <rect x={0} y={0} width={slabLengthMm} height={slabWidthMm} fill="none" stroke="currentColor" strokeWidth={slabLengthMm * 0.003} className="text-text-secondary" />
      {placements.map((p, i) => {
        const x = parseFloat(p.x_mm);
        const y = parseFloat(p.y_mm);
        const w = parseFloat(p.length_mm);
        const h = parseFloat(p.width_mm);
        const color = colorForLabel(p.label, labelOrder.indexOf(p.label));
        return (
          <g key={`${p.label}-${p.instance_index}-${i}`}>
            <rect
              x={x} y={y} width={w} height={h}
              fill={color} fillOpacity={0.25} stroke={color} strokeWidth={slabLengthMm * 0.002}
            />
            <text
              x={x + w / 2} y={y + h / 2}
              fontSize={fontSize} textAnchor="middle" dominantBaseline="middle"
              fill={color} fontWeight={600}
            >
              {p.label} #{p.instance_index}
              {p.rotated ? " ↻" : ""}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
