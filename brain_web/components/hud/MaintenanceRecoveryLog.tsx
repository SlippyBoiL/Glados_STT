"use client";

import { useEffect, useRef } from "react";

type Props = {
  lines: string[];
};

export function MaintenanceRecoveryLog({ lines }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="hud-panel flex min-h-0 flex-1 flex-col overflow-hidden p-3">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
        Live Maintenance &amp; Recovery Log
      </p>
      <div className="flex-1 overflow-y-auto rounded border border-hud-cyan/10 bg-black/50 p-2 font-mono text-[10px] leading-relaxed text-amber-300/90">
        {lines.length === 0 ? (
          <p className="text-hud-cyan/40">
            Reliability Maintenance agent idle — process kills, relaunches, and fixes
            appear here.
          </p>
        ) : (
          lines.map((line, i) => (
            <div key={`${i}-${line.slice(0, 24)}`} className="whitespace-pre-wrap">
              {line}
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
