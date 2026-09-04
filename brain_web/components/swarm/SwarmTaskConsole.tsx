"use client";

import { HudChat } from "@/components/hud/HudChat";
import type { TelemetryEvent } from "@/lib/types";

export function SwarmTaskConsole({ events }: { events: TelemetryEvent[] }) {
  return (
    <section className="rounded-lg border border-aperture-orange/30 bg-aperture-panel/90 shadow-[0_0_24px_rgba(255,140,0,0.06)]">
      <div className="border-b border-aperture-border px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-aperture-orange">
          Assign Task to Swarm
        </h3>
        <p className="mt-1 text-xs text-aperture-muted">
          Type what you want the agents to do, then press Send or Enter. Tasks
          go to the Swarm Manager — voice is optional.
        </p>
      </div>
      <div className="p-3">
        <HudChat
          events={events}
          title="Task channel"
          subtitle="Your prompt, agent replies, and thinking stream appear below."
          className="!h-[min(38vh,400px)] !min-h-[260px] border-aperture-border/60"
        />
      </div>
    </section>
  );
}
