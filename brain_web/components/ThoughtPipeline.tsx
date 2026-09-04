"use client";

import { useMemo } from "react";
import type { TelemetryEvent } from "@/lib/types";
import { buildThoughtTimeline } from "@/lib/hudState";

type Props = {
  events: TelemetryEvent[];
};

const phaseClass: Record<string, string> = {
  heard: "stage-hearing",
  facility: "stage-memory",
  intent: "stage-intent",
  memory: "stage-memory",
  skills: "stage-intent",
  llm: "stage-reason",
  execute: "stage-action",
  learn: "stage-intent",
  speak: "stage-reason",
};

export function ThoughtPipeline({ events }: Props) {
  const timeline = useMemo(() => buildThoughtTimeline(events).slice(-12), [events]);

  return (
    <div className="panel p-4">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-aperture-muted">
        Live cognition (chronological)
      </h2>
      {timeline.length === 0 ? (
        <p className="text-sm text-aperture-muted">
          Waiting for Glados to think… open the{" "}
          <a href="/" className="text-aperture-orange underline">
            Command Center
          </a>{" "}
          to chat and watch thoughts stream in.
        </p>
      ) : (
        <div className="space-y-2">
          {timeline.map((step, i) => (
            <div
              key={`${step.ts}-${i}`}
              className={`rounded border-l-4 bg-black/20 px-3 py-2 ${
                phaseClass[step.phase] || "stage-reason"
              } ${step.active ? "ring-1 ring-aperture-orange/40" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase text-aperture-orange">
                  {step.phase}
                </span>
                <span className="font-mono text-[10px] text-aperture-muted">
                  {step.time}
                </span>
              </div>
              <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                {step.message}
              </p>
              {step.detail ? (
                <p className="mt-1 font-mono text-[10px] text-aperture-muted">
                  {step.detail.slice(0, 160)}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
