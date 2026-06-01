"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BrainState, TelemetryEvent } from "@/lib/types";

export default function MonitorPage() {
  const [state, setState] = useState<BrainState | null>(null);
  const [monitorEvents, setMonitorEvents] = useState<TelemetryEvent[]>([]);

  useEffect(() => {
    const load = () => {
      api.state().then(setState);
      api.recent(300).then((r) => {
        setMonitorEvents(
          r.events.filter(
            (e) =>
              e.event_type === "subsystem_status" ||
              e.event_type === "monitor_alert",
          ),
        );
      });
    };
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  const flags = state?.subsystem_flags || {};
  const sub = state?.subsystem_status;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Infrastructure Monitor</h2>
        <p className="text-sm text-aperture-muted">
          Subsystem flags and SSH device health
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["vision_enabled", "Vision"],
          ["monitoring_enabled", "Monitoring"],
          ["cursor_auto_inject", "Cursor inject"],
        ].map(([key, label]) => (
          <div key={key} className="panel p-4">
            <p className="text-xs uppercase text-aperture-muted">{label}</p>
            <p
              className={`mt-1 text-lg font-semibold ${
                flags[key] ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {flags[key] ? "ON" : "OFF"}
            </p>
          </div>
        ))}
        <div className="panel p-4">
          <p className="text-xs uppercase text-aperture-muted">Events</p>
          <p className="mt-1 text-lg font-semibold">{state?.event_count ?? "—"}</p>
        </div>
      </div>

      {sub ? (
        <div className="panel p-4">
          <h3 className="mb-2 text-sm font-semibold text-aperture-orange">
            Latest subsystem snapshot
          </h3>
          <pre className="overflow-x-auto text-xs text-aperture-muted">
            {JSON.stringify(sub, null, 2)}
          </pre>
        </div>
      ) : null}

      {state?.last_monitor_alert ? (
        <div className="panel border-red-500/30 p-4">
          <h3 className="text-sm font-semibold text-red-400">Last alert</h3>
          <pre className="mt-2 text-xs">
            {JSON.stringify(state.last_monitor_alert, null, 2)}
          </pre>
        </div>
      ) : null}

      <div className="panel p-4">
        <h3 className="mb-3 text-sm font-semibold uppercase text-aperture-muted">
          Monitor history
        </h3>
        <div className="max-h-96 space-y-2 overflow-y-auto font-mono text-xs">
          {[...monitorEvents].reverse().map((ev, i) => (
            <div
              key={i}
              className="rounded border border-aperture-border/50 bg-black/20 px-2 py-1"
            >
              <span className="text-aperture-muted">
                {new Date(ev.ts * 1000).toLocaleString()}{" "}
              </span>
              <span className="text-aperture-orange">{ev.event_type}</span>
              <pre className="mt-1 whitespace-pre-wrap text-aperture-muted">
                {JSON.stringify(ev.payload)}
              </pre>
            </div>
          ))}
          {monitorEvents.length === 0 ? (
            <p className="text-aperture-muted">No monitor events yet.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
