"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

/** A canvas-based signature capture -- no external dependency, matching the
 * app's pattern of hand-building small interactive surfaces (see
 * components/ui/charts.tsx) rather than adding a library for one widget. */
export function SignaturePad({ onCapture }: { onCapture: (file: File) => void }) {
  const t = useTranslations("installation");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);
  const [hasDrawn, setHasDrawn] = useState(false);
  const [saving, setSaving] = useState(false);

  function pointFromEvent(e: React.MouseEvent | React.TouchEvent): { x: number; y: number } {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const source = "touches" in e ? e.touches[0] : e;
    return { x: (source.clientX - rect.left) * scaleX, y: (source.clientY - rect.top) * scaleY };
  }

  function handleStart(e: React.MouseEvent | React.TouchEvent) {
    drawingRef.current = true;
    const ctx = canvasRef.current!.getContext("2d")!;
    const { x, y } = pointFromEvent(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  function handleMove(e: React.MouseEvent | React.TouchEvent) {
    if (!drawingRef.current) return;
    e.preventDefault();
    const ctx = canvasRef.current!.getContext("2d")!;
    const { x, y } = pointFromEvent(e);
    ctx.strokeStyle = "#16181D";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasDrawn(true);
  }

  function handleEnd() {
    drawingRef.current = false;
  }

  function handleClear() {
    const canvas = canvasRef.current!;
    canvas.getContext("2d")!.clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  }

  function handleSave() {
    setSaving(true);
    canvasRef.current!.toBlob((blob) => {
      setSaving(false);
      if (blob) onCapture(new File([blob], "signature.png", { type: "image/png" }));
    }, "image/png");
  }

  return (
    <div className="flex flex-col gap-2">
      <canvas
        ref={canvasRef}
        width={600}
        height={200}
        className="w-full touch-none rounded-md border border-border bg-surface"
        style={{ height: 160 }}
        onMouseDown={handleStart}
        onMouseMove={handleMove}
        onMouseUp={handleEnd}
        onMouseLeave={handleEnd}
        onTouchStart={handleStart}
        onTouchMove={handleMove}
        onTouchEnd={handleEnd}
      />
      <div className="flex gap-2">
        <Button variant="secondary" onClick={handleClear} disabled={!hasDrawn}>
          {t("clearSignature")}
        </Button>
        <Button onClick={handleSave} disabled={!hasDrawn || saving}>
          {saving ? t("saving") : t("saveSignature")}
        </Button>
      </div>
    </div>
  );
}
