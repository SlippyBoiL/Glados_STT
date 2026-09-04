"use client";

import { useEffect, useRef } from "react";
import type { TerminalLine } from "@/lib/types";

type Props = {
  lines?: string[];
  terminalLog?: TerminalLine[];
};

export function InternalMonologue({ lines = [], terminalLog }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const rows: TerminalLine[] =
    terminalLog ??
    lines.map((text, i) => ({
      id: `legacy-${i}`,
      kind: "telemetry" as const,
      text,
    }));

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rows.length]);

  return (
    <div className="panel flex h-full min-h-[200px] flex-col overflow-hidden">
      <p className="border-b border-aperture-border px-3 py-2 text-xs uppercase tracking-widest text-aperture-muted">
        Internal Monologue
      </p>
      <div className="flex-1 overflow-y-auto bg-black/40 p-3 font-mono text-[11px] leading-relaxed">
        {rows.length === 0 ? (
          <p className="text-aperture-muted">Awaiting telemetry…</p>
        ) : (
          rows.map((row) => {
            if (row.kind === "tool_intent") {
              return (
                <div
                  key={row.id}
                  className="whitespace-pre-wrap text-amber-500"
                >
                  {row.text}
                </div>
              );
            }
            if (row.kind === "tool_result") {
              return (
                <div
                  key={row.id}
                  className="whitespace-pre-wrap pl-2 text-cyan-800/80 dark:text-gray-400"
                >
                  {row.text}
                </div>
              );
            }
            return (
              <div
                key={row.id}
                className="whitespace-pre-wrap text-emerald-400/90"
              >
                {row.text}
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
