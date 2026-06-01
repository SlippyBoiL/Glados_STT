"use client";

type Props = {
  label: string;
  value: number;
  unit?: string;
  detail?: string;
};

export function MetricBar({ label, value, unit = "%", detail }: Props) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="mb-3">
      <div className="mb-1 flex justify-between font-mono text-[10px] uppercase tracking-wider text-hud-cyan/80">
        <span>{label}</span>
        <span>
          {value.toFixed(1)}
          {unit}
          {detail ? ` · ${detail}` : ""}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-hud-grid">
        <div
          className="h-full rounded-full bg-gradient-to-r from-hud-glow to-hud-cyan transition-all duration-500"
          style={{ width: `${pct}%`, boxShadow: "0 0 8px rgba(61, 214, 255, 0.6)" }}
        />
      </div>
    </div>
  );
}
