"use client";

import { useEffect, useRef } from "react";

type Props = {
  lines: string[];
};

export function MaintenanceLog({ lines }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="panel flex max-h-[180px] flex-col overflow-hidden">
      <p className="border-b border-aperture-border px-3 py-2 text-xs uppercase tracking-widest text-aperture-muted">
        Maintenance Log
      </p>
      <div className="flex-1 overflow-y-auto bg-black/50 p-2 font-mono text-[10px] leading-relaxed text-amber-300/90">
        {lines.length === 0 ? (
          <p className="text-aperture-muted">No interventions yet.</p>
        ) : (
          lines.map((line, i) => (
            <div key={`${i}-${line.slice(0, 20)}`}>{line}</div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
