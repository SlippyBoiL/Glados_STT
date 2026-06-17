"use client";

import { useEffect, useRef } from "react";

type Props = {
  lines: string[];
};

export function InternalMonologue({ lines }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="panel flex h-full min-h-[200px] flex-col overflow-hidden">
      <p className="border-b border-aperture-border px-3 py-2 text-xs uppercase tracking-widest text-aperture-muted">
        Internal Monologue
      </p>
      <div className="flex-1 overflow-y-auto bg-black/40 p-3 font-mono text-[11px] leading-relaxed text-emerald-400/90">
        {lines.length === 0 ? (
          <p className="text-aperture-muted">Awaiting telemetry…</p>
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
