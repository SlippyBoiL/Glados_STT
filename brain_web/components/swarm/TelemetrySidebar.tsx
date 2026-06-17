"use client";

import type { SwarmDashboardState } from "@/lib/types";

function MetricTile({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="rounded border border-aperture-border/60 bg-aperture-bg/30 p-2">
      <div className="flex justify-between text-[10px] uppercase tracking-wider text-aperture-muted">
        <span>{label}</span>
        <span>{pct.toFixed(0)}%</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded bg-aperture-border/40">
        <div
          className="h-full rounded bg-aperture-orange transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

type Props = {
  swarm: SwarmDashboardState;
  connected: boolean;
};

export function TelemetrySidebar({ swarm, connected }: Props) {
  return (
    <div className="flex h-full flex-col gap-3">
      <div className="panel p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs uppercase tracking-widest text-aperture-muted">
            System Vitals
          </p>
          <span
            className={`text-[10px] ${connected ? "text-emerald-400" : "text-red-400"}`}
          >
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
        <div className="grid gap-2">
          <MetricTile label="CPU" value={swarm.metrics.cpu} />
          <MetricTile label="RAM" value={swarm.metrics.ram} />
          <MetricTile label="Disk" value={swarm.metrics.disk} />
        </div>
      </div>

      <div className="panel flex-1 overflow-hidden p-3">
        <p className="mb-2 text-xs uppercase tracking-widest text-aperture-muted">
          Service Registry
        </p>
        <ul className="space-y-2 overflow-y-auto">
          {swarm.services.map((svc) => (
            <li
              key={svc.id}
              className="rounded border border-aperture-border/50 px-2 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-aperture-text">{svc.name}</span>
                <span
                  className={`h-2 w-2 rounded-full ${svc.ok ? "bg-emerald-500" : "bg-red-500 animate-pulse"}`}
                />
              </div>
              {!svc.ok && svc.alerts.length > 0 ? (
                <p className="mt-1 truncate text-[10px] text-red-400/80">
                  {svc.alerts.join(" · ")}
                </p>
              ) : (
                <p className="mt-1 text-[10px] text-aperture-muted">Connected</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
