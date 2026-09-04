"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ActiveAgentMonologue } from "@/components/hud/ActiveAgentMonologue";
import { CommandOverrideBar } from "@/components/hud/CommandOverrideBar";
import { HudChat } from "@/components/hud/HudChat";
import { JarvisOrb } from "@/components/hud/JarvisOrb";
import { MaintenanceRecoveryLog } from "@/components/hud/MaintenanceRecoveryLog";
import { MetricBar } from "@/components/hud/MetricBar";
import { Radar } from "@/components/hud/Radar";
import { SwarmRoster } from "@/components/hud/SwarmRoster";
import { Waveform } from "@/components/hud/Waveform";
import { api, type SystemMetrics } from "@/lib/api";
import { deriveVoiceState, lastSubtitle } from "@/lib/hudState";
import { buildSwarmState } from "@/lib/swarmState";
import { useLiveTelemetry } from "@/lib/ws";
import type { SwarmDashboardState, TelemetryEvent } from "@/lib/types";

/** Aperture Terminal — 3-panel: Service Status | Interaction Stream | Live Telemetry */
export function CommandCenter() {
  const { events, connected } = useLiveTelemetry(500);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [swarm, setSwarm] = useState<SwarmDashboardState>(() =>
    buildSwarmState([]),
  );
  const voiceState = deriveVoiceState(events);
  const subtitle = lastSubtitle(events);

  useEffect(() => {
    setSwarm(buildSwarmState(events));
  }, [events]);

  useEffect(() => {
    const load = () => {
      api
        .metrics()
        .then((m) => {
          setMetrics(m);
          setSwarm((prev) => ({
            ...prev,
            metrics: {
              cpu: m.cpu_percent ?? prev.metrics.cpu,
              ram: m.ram_percent ?? prev.metrics.ram,
              disk: m.disk_percent ?? prev.metrics.disk,
            },
          }));
        })
        .catch(() => {});
    };
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, []);

  const netTotal =
    (metrics?.network_sent_kbps || 0) + (metrics?.network_recv_kbps || 0);
  const netPct = Math.min(100, netTotal / 50);

  const linkedLabel = useMemo(
    () => (connected ? "● LINKED" : "○ OFFLINE"),
    [connected],
  );

  const recentAnomalies = useMemo(() => {
    return events
      .filter(
        (e) =>
          e.event_type === "watchdog_anomaly" ||
          e.event_type === "monitor_alert" ||
          e.event_type === "subsystem_status",
      )
      .slice(-8)
      .reverse();
  }, [events]);

  const thinkingFeed = useMemo(() => {
    const kept: TelemetryEvent[] = [];
    let lastCot: TelemetryEvent | null = null;
    for (const e of events) {
      if (e.event_type === "hud_chat" && e.payload?.role === "thinking") {
        lastCot = e;
        continue;
      }
      if (
        e.event_type === "thinking" ||
        e.event_type === "swarm_telemetry" ||
        e.event_type === "system_metrics"
      ) {
        kept.push(e);
      }
    }
    if (lastCot) kept.push(lastCot);
    return kept.slice(-24).reverse();
  }, [events]);

  return (
    <div className="hud-root relative min-h-screen overflow-hidden bg-hud-bg text-hud-cyan">
      <div className="hud-grid pointer-events-none absolute inset-0" />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          background:
            "radial-gradient(ellipse at 20% 0%, #3d5c3a 0%, transparent 45%), radial-gradient(ellipse at 80% 100%, #1a3a2a 0%, transparent 40%)",
        }}
      />

      <header className="relative z-10 flex items-center justify-between border-b border-hud-cyan/15 px-6 py-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-amber-500/70">
            Aperture Science Enrichment Center
          </p>
          <h1 className="font-[family-name:var(--font-orbitron,ui-sans-serif)] text-lg font-light tracking-[0.12em] text-hud-cyan md:text-xl">
            APERTURE TERMINAL
          </h1>
          <p className="mt-0.5 font-mono text-[10px] text-hud-cyan/40">
            G.L.a.D.O.S. · Hermes local cognitive engine · Service / Stream /
            Telemetry
          </p>
        </div>
        <div className="flex items-center gap-4 font-mono text-xs">
          <span className={connected ? "text-emerald-400" : "text-red-400"}>
            {linkedLabel}
          </span>
          <span className="text-hud-cyan/40">{metrics?.hostname || "—"}</span>
          <Link
            href="/observatory/"
            className="rounded border border-hud-cyan/20 px-2 py-1 text-hud-cyan/60 transition hover:border-amber-500/40 hover:text-amber-200"
          >
            Observatory
          </Link>
        </div>
      </header>

      <div className="relative z-10 grid min-h-[calc(100vh-64px)] grid-cols-1 gap-3 p-4 lg:grid-cols-[minmax(0,28fr)_minmax(0,44fr)_minmax(0,28fr)]">
        {/* Panel 1 — Service Status */}
        <aside className="flex min-h-0 flex-col gap-3">
          <div className="hud-panel flex-1 p-4">
            <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.28em] text-amber-500/80">
              Panel 01 · Service Status
            </p>
            <p className="mb-4 font-mono text-[9px] text-hud-cyan/40">
              Facility services · host vitals · anomaly watch
            </p>
            <MetricBar
              label="CPU"
              value={metrics?.cpu_percent ?? swarm.metrics.cpu}
            />
            <MetricBar
              label="RAM"
              value={metrics?.ram_percent ?? swarm.metrics.ram}
              detail={
                metrics
                  ? `${metrics.ram_used_gb}/${metrics.ram_total_gb} GB`
                  : undefined
              }
            />
            <MetricBar
              label="Disk"
              value={metrics?.disk_percent ?? swarm.metrics.disk}
              detail={
                metrics
                  ? `${metrics.disk_used_gb}/${metrics.disk_total_gb} GB`
                  : undefined
              }
            />
            <MetricBar
              label="Network"
              value={netPct}
              unit=" kbps"
              detail={
                metrics
                  ? `↑${metrics.network_sent_kbps} ↓${metrics.network_recv_kbps}`
                  : undefined
              }
            />
            <div className="mt-4 border-t border-hud-cyan/10 pt-3">
              <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.2em] text-hud-cyan/50">
                Recent alerts
              </p>
              <ul className="max-h-36 space-y-1 overflow-y-auto font-mono text-[10px] text-hud-cyan/70">
                {recentAnomalies.length === 0 && (
                  <li className="text-hud-cyan/30">No anomalies recorded</li>
                )}
                {recentAnomalies.map((ev, i) => {
                  const p = (ev.payload || {}) as Record<string, unknown>;
                  const label =
                    String(p.message || p.device || ev.event_type || "event");
                  return (
                    <li key={`${ev.ts}-${i}`} className="truncate">
                      <span className="text-amber-500/70">▸</span> {label}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
          <SwarmRoster swarm={swarm} />
        </aside>

        {/* Panel 2 — Interaction Stream */}
        <section className="flex min-h-0 flex-col gap-3">
          <div className="hud-panel shrink-0 px-4 py-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-amber-500/80">
              Panel 02 · Interaction Stream
            </p>
          </div>
          <div className="shrink-0">
            <JarvisOrb voiceState={voiceState} />
          </div>
          <div className="hud-panel mx-auto w-full max-w-2xl shrink-0 px-6 py-3 text-center">
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-hud-cyan/50">
              Latest vocalization
            </p>
            <p className="mt-2 text-sm leading-relaxed text-hud-cyan/90 md:text-base">
              {subtitle || "Awaiting subject interaction…"}
            </p>
          </div>
          <div className="hud-panel shrink-0 p-2">
            <Waveform voiceState={voiceState} />
          </div>
          <ActiveAgentMonologue swarm={swarm} />
          <HudChat events={events} className="min-h-[220px] flex-1" />
          <div className="hud-panel shrink-0 p-3">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan/70">
              Command override — Enter to dispatch
            </p>
            <CommandOverrideBar connected={connected} />
          </div>
        </section>

        {/* Panel 3 — Live Telemetry */}
        <aside className="flex min-h-0 flex-col gap-3">
          <div className="hud-panel shrink-0 px-4 py-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-amber-500/80">
              Panel 03 · Live Telemetry
            </p>
          </div>
          <div className="hud-panel shrink-0 p-4">
            <Radar />
          </div>
          <div className="hud-panel min-h-0 flex-1 overflow-hidden p-3">
            <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.2em] text-hud-cyan/50">
              Thought / swarm stream
            </p>
            <ul className="max-h-[280px] space-y-1.5 overflow-y-auto font-mono text-[10px] leading-snug text-hud-cyan/65">
              {thinkingFeed.length === 0 && (
                <li className="text-hud-cyan/30">Telemetry idle</li>
              )}
              {thinkingFeed.map((ev, i) => {
                const p = (ev.payload || {}) as Record<string, unknown>;
                const msg = String(
                  p.message || p.text || p.phase || ev.event_type || "",
                ).slice(0, 160);
                return (
                  <li key={`tel-${ev.ts}-${i}`}>
                    <span className="text-emerald-500/60">
                      {String(ev.event_type).slice(0, 12)}
                    </span>{" "}
                    {msg}
                  </li>
                );
              })}
            </ul>
          </div>
          <MaintenanceRecoveryLog lines={swarm.maintenanceLog} />
        </aside>
      </div>

      <footer className="relative z-10 border-t border-hud-cyan/10 py-2 text-center font-mono text-[9px] uppercase tracking-[0.4em] text-hud-cyan/30">
        For science · Fullscreen recommended (F11)
      </footer>
    </div>
  );
}
