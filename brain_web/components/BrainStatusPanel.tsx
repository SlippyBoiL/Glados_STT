"use client";

import Link from "next/link";
import type { BrainState, TelemetryEvent } from "@/lib/types";
import { currentThoughtPhase } from "@/lib/hudState";

type Props = {
  state: BrainState | null;
  events: TelemetryEvent[];
  connected: boolean;
  variant?: "hud" | "observatory";
};

function Row({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2 py-1">
      <span className="text-aperture-muted">{label}</span>
      <span className={`truncate font-mono text-xs ${valueClass || "text-aperture-text"}`}>
        {value}
      </span>
    </div>
  );
}

export function BrainStatusPanel({
  state,
  events,
  connected,
  variant = "observatory",
}: Props) {
  const phase = currentThoughtPhase(events);
  const llm = state?.llm_config;
  const isHud = variant === "hud";

  const shell = isHud
    ? "hud-panel p-4 font-mono text-[10px]"
    : "panel p-4";

  return (
    <div className={shell}>
      <div className="mb-3 flex items-center justify-between">
        <p
          className={
            isHud
              ? "uppercase tracking-[0.2em] text-hud-cyan"
              : "text-sm font-semibold text-aperture-muted"
          }
        >
          Brain Status
        </p>
        <span className={connected ? "text-emerald-400" : "text-red-400"}>
          {connected ? "● LIVE" : "○ OFFLINE"}
        </span>
      </div>

      <div className={isHud ? "space-y-1 text-hud-cyan/70" : "space-y-1 text-sm"}>
        <Row
          label="Phase"
          value={phase}
          valueClass={isHud ? "text-hud-cyan" : "text-aperture-orange"}
        />
        <Row
          label="LLM"
          value={`${llm?.provider || "?"} · ${llm?.model || "—"}`}
        />
        {llm?.vision_model ? (
          <Row label="Vision" value={llm.vision_model} />
        ) : null}
        <Row
          label="Memory"
          value={
            state?.computer_brain?.fact_count != null
              ? `${state.computer_brain.fact_count} PC facts`
              : "—"
          }
        />
        <Row
          label="Protocols"
          value={state?.skills_count != null ? String(state.skills_count) : "—"}
        />
        <Row
          label="Events"
          value={state?.event_count != null ? String(state.event_count) : "—"}
        />
        {state?.last_thinking?.message ? (
          <div className={`mt-2 border-t pt-2 ${isHud ? "border-hud-cyan/10" : "border-aperture-border/40"}`}>
            <p className={isHud ? "text-hud-cyan/40" : "text-aperture-muted"}>
              Latest thought
            </p>
            <p className={`mt-1 text-xs ${isHud ? "text-hud-cyan/80" : ""}`}>
              [{String(state.last_thinking.phase || "think")}]{" "}
              {String(state.last_thinking.message || "").slice(0, 140)}
            </p>
          </div>
        ) : null}
      </div>

      {!isHud ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href="/"
            className="rounded border border-aperture-orange/40 px-3 py-1.5 text-xs text-aperture-orange hover:bg-aperture-orange/10"
          >
            Command Center →
          </Link>
          <Link
            href="/memory/"
            className="rounded border border-aperture-border px-3 py-1.5 text-xs text-aperture-muted hover:text-aperture-text"
          >
            Memory graph
          </Link>
          <Link
            href="/skills/"
            className="rounded border border-aperture-border px-3 py-1.5 text-xs text-aperture-muted hover:text-aperture-text"
          >
            Skills
          </Link>
        </div>
      ) : null}
    </div>
  );
}
