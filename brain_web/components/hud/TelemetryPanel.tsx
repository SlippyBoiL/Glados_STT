"use client";

import { useEffect, useRef } from "react";
import type { TelemetryEvent } from "@/lib/types";
import { formatTelemetryLine } from "@/lib/hudState";

type Props = {
  events: TelemetryEvent[];
};

export function TelemetryPanel({ events }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const lines = events.slice(-30).map(formatTelemetryLine);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines.length]);

  return (
    <div className="hud-panel flex h-full flex-col p-3">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
        Telemetry
      </p>
      <div
        ref={ref}
        className="flex-1 overflow-y-auto font-mono text-[10px] leading-relaxed text-hud-cyan/60"
      >
        {lines.length === 0 ? (
          <span className="text-hud-cyan/30">Awaiting enrichment data…</span>
        ) : (
          lines.map((line, i) => (
            <div key={i} className="border-b border-hud-cyan/5 py-0.5">
              {line}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
