"use client";

import { useMemo } from "react";
import type { TelemetryEvent } from "@/lib/types";
import { buildThoughtTimeline, type ThoughtItem } from "@/lib/hudState";

const phaseColors: Record<string, string> = {
  heard: "border-hud-cyan/40 text-hud-cyan",
  facility: "border-violet-400/40 text-violet-300",
  task: "border-amber-400/40 text-amber-300",
  learn: "border-orange-400/40 text-orange-300",
  research: "border-sky-400/40 text-sky-300",
  memory: "border-emerald-400/40 text-emerald-300",
  skills: "border-orange-300/40 text-orange-200",
  llm: "border-hud-cyan/50 text-hud-cyan",
  execute: "border-red-400/40 text-red-300",
  speak: "border-hud-cyan/30 text-hud-cyan/80",
  system: "border-hud-cyan/20 text-hud-cyan/60",
};

type Props = {
  events: TelemetryEvent[];
};

function ThoughtRow({ item }: { item: ThoughtItem }) {
  const color = phaseColors[item.phase] || phaseColors.system;
  const active = item.active;

  return (
    <div
      className={`relative border-l-2 py-1.5 pl-3 pr-1 ${color} ${
        active ? "bg-hud-cyan/5" : ""
      }`}
    >
      {active ? (
        <span className="absolute -left-[5px] top-2 h-2 w-2 animate-pulse rounded-full bg-hud-cyan shadow-[0_0_8px_#22d3ee]" />
      ) : null}
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[9px] uppercase tracking-wider opacity-70">
          {item.phase}
        </span>
        <span className="font-mono text-[9px] text-hud-cyan/30">
          {item.time}
        </span>
      </div>
      <p className="mt-0.5 text-[11px] leading-snug text-hud-cyan/90">
        {item.message}
      </p>
      {item.detail ? (
        <p className="mt-0.5 truncate font-mono text-[9px] text-hud-cyan/40">
          {item.detail}
        </p>
      ) : null}
    </div>
  );
}

export function ThoughtProcess({ events }: Props) {
  const timeline = useMemo(() => buildThoughtTimeline(events), [events]);
  const thinkingOnly = timeline.filter((t) => t.source === "thinking");

  return (
    <div className="hud-panel flex h-full min-h-[220px] flex-col p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
          Thought Process
        </p>
        <span className="font-mono text-[9px] text-hud-cyan/40">
          {thinkingOnly.length} steps
        </span>
      </div>
      <div className="flex-1 space-y-0 overflow-y-auto">
        {timeline.length === 0 ? (
          <p className="font-mono text-[10px] text-hud-cyan/30">
            Awaiting cognition stream…
          </p>
        ) : (
          timeline.map((item, i) => <ThoughtRow key={`${item.ts}-${i}`} item={item} />)
        )}
      </div>
    </div>
  );
}
