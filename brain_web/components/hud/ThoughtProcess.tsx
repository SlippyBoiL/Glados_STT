"use client";

import { useMemo, useState } from "react";
import type { TelemetryEvent } from "@/lib/types";
import {
  buildThoughtTimeline,
  groupThoughtTimeline,
  type ThoughtItem,
} from "@/lib/hudState";

const phaseColors: Record<string, string> = {
  heard: "border-cyan-400/50 text-cyan-300",
  facility: "border-violet-400/40 text-violet-300",
  intent: "border-fuchsia-400/40 text-fuchsia-300",
  task: "border-amber-400/40 text-amber-300",
  learn: "border-orange-400/40 text-orange-300",
  browser: "border-sky-400/40 text-sky-300",
  research: "border-sky-400/40 text-sky-300",
  memory: "border-emerald-400/40 text-emerald-300",
  skills: "border-orange-300/40 text-orange-200",
  llm: "border-cyan-400/50 text-cyan-200",
  execute: "border-red-400/40 text-red-300",
  organize: "border-lime-400/40 text-lime-300",
  admin: "border-yellow-400/40 text-yellow-200",
  action: "border-rose-400/40 text-rose-300",
  speak: "border-cyan-300/30 text-cyan-100",
  monitor: "border-red-300/40 text-red-200",
  idle: "border-slate-400/30 text-slate-300",
  chat: "border-cyan-400/30 text-cyan-200",
  system: "border-slate-500/30 text-slate-400",
};

type Props = {
  events: TelemetryEvent[];
  variant?: "hud" | "observatory";
  groupByTurn?: boolean;
};

function ThoughtRow({
  item,
  variant,
}: {
  item: ThoughtItem;
  variant: "hud" | "observatory";
}) {
  const [expanded, setExpanded] = useState(false);
  const color = phaseColors[item.phase] || phaseColors.system;
  const active = item.active;
  const panelBg =
    variant === "hud"
      ? active
        ? "bg-hud-cyan/5"
        : ""
      : active
        ? "bg-aperture-orange/5"
        : "";

  return (
    <div
      className={`relative border-l-2 py-1.5 pl-3 pr-1 ${color} ${panelBg}`}
    >
      {active ? (
        <span
          className={`absolute -left-[5px] top-2 h-2 w-2 animate-pulse rounded-full shadow-[0_0_8px_currentColor] ${
            variant === "hud" ? "bg-hud-cyan" : "bg-aperture-orange"
          }`}
        />
      ) : null}
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[9px] uppercase tracking-wider opacity-70">
          {item.phase}
        </span>
        <span
          className={`font-mono text-[9px] ${
            variant === "hud" ? "text-hud-cyan/30" : "text-aperture-muted"
          }`}
        >
          {item.time}
        </span>
      </div>
      <p
        className={`mt-0.5 text-[11px] leading-snug ${
          variant === "hud" ? "text-hud-cyan/90" : "text-aperture-text"
        }`}
      >
        {item.message}
      </p>
      {item.detail ? (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className={`mt-0.5 block w-full text-left font-mono text-[9px] ${
            variant === "hud" ? "text-hud-cyan/50 hover:text-hud-cyan/80" : "text-aperture-muted hover:text-aperture-orange"
          }`}
        >
          {expanded ? item.detail : `${item.detail.slice(0, 72)}${item.detail.length > 72 ? "… (tap)" : ""}`}
        </button>
      ) : null}
    </div>
  );
}

export function ThoughtProcess({
  events,
  variant = "hud",
  groupByTurn = true,
}: Props) {
  const timeline = useMemo(() => buildThoughtTimeline(events), [events]);
  const turns = useMemo(
    () => (groupByTurn ? groupThoughtTimeline(timeline) : []),
    [timeline, groupByTurn],
  );
  const thinkingCount = timeline.filter((t) => t.source === "thinking").length;

  const shellClass =
    variant === "hud"
      ? "hud-panel flex h-full min-h-[220px] flex-col p-3"
      : "panel flex min-h-[320px] flex-col p-4";

  const titleClass =
    variant === "hud"
      ? "font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan"
      : "text-sm font-semibold uppercase tracking-wider text-aperture-muted";

  return (
    <div className={shellClass}>
      <div className="mb-2 flex items-center justify-between">
        <p className={titleClass}>Thought Process</p>
        <span
          className={`font-mono text-[9px] ${
            variant === "hud" ? "text-hud-cyan/40" : "text-aperture-muted"
          }`}
        >
          {thinkingCount} cognition steps · {timeline.length} events
        </span>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {timeline.length === 0 ? (
          <p
            className={`font-mono text-[10px] ${
              variant === "hud" ? "text-hud-cyan/30" : "text-aperture-muted"
            }`}
          >
            Awaiting cognition stream… send a message or speak to GLaDOS.
          </p>
        ) : groupByTurn && turns.length > 1 ? (
          turns.map((turn) => (
            <div key={turn.id}>
              <p
                className={`mb-1 font-mono text-[9px] uppercase tracking-wider ${
                  variant === "hud" ? "text-hud-cyan/40" : "text-aperture-muted"
                }`}
              >
                {turn.label}
              </p>
              <div className="space-y-0">
                {turn.items.map((item, i) => (
                  <ThoughtRow key={`${turn.id}-${item.ts}-${i}`} item={item} variant={variant} />
                ))}
              </div>
            </div>
          ))
        ) : (
          timeline.map((item, i) => (
            <ThoughtRow key={`${item.ts}-${i}`} item={item} variant={variant} />
          ))
        )}
      </div>
    </div>
  );
}
