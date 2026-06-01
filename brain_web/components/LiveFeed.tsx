"use client";

import type { TelemetryEvent } from "@/lib/types";

const colors: Record<string, string> = {
  heard: "text-aperture-blue",
  memory_retrieved: "text-emerald-400",
  intent_classified: "text-violet-400",
  skills_matched: "text-violet-300",
  llm_response: "text-aperture-orange",
  code_executed: "text-red-400",
  monitor_alert: "text-red-300",
  facility_scan: "text-cyan-400",
  facility_brain: "text-cyan-300",
  skill_learned: "text-amber-400",
  thinking: "text-amber-200",
  subsystem_status: "text-aperture-muted",
  cursor_prompt: "text-aperture-muted",
};

type Props = {
  events: TelemetryEvent[];
  connected: boolean;
};

export function LiveFeed({ events, connected }: Props) {
  const feed = [...events].reverse().slice(0, 40);

  return (
    <div className="panel flex h-full min-h-[320px] flex-col p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-aperture-muted">
          Live Feed
        </h2>
        <span
          className={`text-xs ${connected ? "text-emerald-400" : "text-red-400"}`}
        >
          {connected ? "● connected" : "○ reconnecting"}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto font-mono text-xs">
        {feed.length === 0 ? (
          <p className="text-aperture-muted">No telemetry yet.</p>
        ) : (
          feed.map((ev, i) => (
            <div
              key={`${ev.ts}-${ev.event_type}-${i}`}
              className="rounded border border-aperture-border/50 bg-black/20 px-2 py-1.5"
            >
              <div className="flex gap-2">
                <span className="text-aperture-muted">
                  {new Date(ev.ts * 1000).toLocaleTimeString()}
                </span>
                <span className={colors[ev.event_type] || "text-aperture-text"}>
                  {ev.event_type}
                </span>
              </div>
              <pre className="mt-1 max-h-24 overflow-hidden whitespace-pre-wrap break-words text-aperture-muted">
                {JSON.stringify(ev.payload, null, 0).slice(0, 400)}
              </pre>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
