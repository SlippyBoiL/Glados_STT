"use client";

import { useEffect, useState } from "react";
import { BrainCanvas } from "@/components/BrainCanvas";
import { LiveFeed } from "@/components/LiveFeed";
import { ThoughtPipeline } from "@/components/ThoughtPipeline";
import { api } from "@/lib/api";
import { useLiveTelemetry } from "@/lib/ws";
import type { BrainState } from "@/lib/types";

export default function LiveMindPage() {
  const { events, connected } = useLiveTelemetry();
  const [state, setState] = useState<BrainState | null>(null);
  const lastEvent = events[events.length - 1];

  useEffect(() => {
    api.state().then(setState).catch(() => {});
    const t = setInterval(() => {
      api.state().then(setState).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold">Live Mind</h2>
          <p className="text-sm text-aperture-muted">
            Real-time thought pipeline from Glados telemetry
          </p>
        </div>
        {state?.event_count != null ? (
          <span className="font-mono text-xs text-aperture-muted">
            {state.event_count} events logged
          </span>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <BrainCanvas activeEventType={lastEvent?.event_type} />
        <div className="lg:col-span-2">
          <ThoughtPipeline events={events} />
        </div>
      </div>

      <LiveFeed events={events} connected={connected} />

      {state?.last_heard?.text ? (
        <p className="text-center text-xs text-aperture-muted">
          Last heard: &ldquo;{state.last_heard.text}&rdquo;
        </p>
      ) : null}
    </div>
  );
}
