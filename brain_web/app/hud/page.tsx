"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ActiveAgentMonologue } from "@/components/hud/ActiveAgentMonologue";
import { CommandOverrideBar } from "@/components/hud/CommandOverrideBar";
import { JarvisOrb } from "@/components/hud/JarvisOrb";
import { MaintenanceRecoveryLog } from "@/components/hud/MaintenanceRecoveryLog";
import { MetricBar } from "@/components/hud/MetricBar";
import { Radar } from "@/components/hud/Radar";
import { SwarmRoster } from "@/components/hud/SwarmRoster";
import { Waveform } from "@/components/hud/Waveform";
import { api, type SystemMetrics } from "@/lib/api";
import { deriveVoiceState, lastSubtitle } from "@/lib/hudState";
import { buildSwarmState, isManagerBusy } from "@/lib/swarmState";
import { useLiveTelemetry } from "@/lib/ws";
import type { SwarmDashboardState } from "@/lib/types";

export default function CommandCenterPage() {
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
      api.metrics().then((m) => {
        setMetrics(m);
        setSwarm((prev) => ({
          ...prev,
          metrics: {
            cpu: m.cpu_percent ?? prev.metrics.cpu,
            ram: m.ram_percent ?? prev.metrics.ram,
            disk: m.disk_percent ?? prev.metrics.disk,
          },
        }));
      }).catch(() => {});
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

  const managerBusy = useMemo(() => isManagerBusy(swarm), [swarm]);

  return (
    <div className="hud-root relative min-h-screen overflow-hidden bg-hud-bg text-hud-cyan">
      <div className="hud-grid pointer-events-none absolute inset-0" />

      <header className="relative z-10 flex items-center justify-between border-b border-hud-cyan/10 px-6 py-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-hud-cyan/50">
            Aperture Science Enrichment Center
          </p>
          <h1 className="text-lg font-light tracking-wide text-hud-cyan md:text-xl">
            G.L.a.D.O.S. — Genetic Lifeform and Disk Operating System
          </h1>
        </div>
        <div className="flex items-center gap-4 font-mono text-xs">
          <span className={connected ? "text-emerald-400" : "text-red-400"}>
            {linkedLabel}
          </span>
          <span className="text-hud-cyan/40">{metrics?.hostname || "—"}</span>
          <Link
            href="/"
            className="rounded border border-hud-cyan/20 px-2 py-1 text-hud-cyan/60 hover:text-hud-cyan"
          >
            Swarm Dashboard
          </Link>
        </div>
      </header>

      {/* 30% | 45% | 25% swarm command grid */}
      <div className="relative z-10 grid min-h-[calc(100vh-56px)] grid-cols-1 gap-3 p-4 lg:grid-cols-[minmax(0,30fr)_minmax(0,45fr)_minmax(0,25fr)]">
        {/* Left — metrics + roster */}
        <aside className="flex min-h-0 flex-col gap-3">
          <div className="hud-panel shrink-0 p-4">
            <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
              System Metrics
            </p>
            <MetricBar label="CPU" value={metrics?.cpu_percent ?? swarm.metrics.cpu} />
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
          </div>
          <SwarmRoster swarm={swarm} />
        </aside>

        {/* Center — core, visualizer, agent monologue */}
        <section className="flex min-h-0 flex-col gap-3">
          <div className="shrink-0">
            <JarvisOrb voiceState={voiceState} />
          </div>
          <div className="hud-panel mx-auto w-full max-w-2xl shrink-0 px-6 py-3 text-center">
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-hud-cyan/50">
              Latest output
            </p>
            <p className="mt-2 text-sm leading-relaxed text-hud-cyan/90 md:text-base">
              {subtitle}
            </p>
          </div>
          <div className="hud-panel shrink-0 p-2">
            <Waveform voiceState={voiceState} />
          </div>
          <ActiveAgentMonologue swarm={swarm} />
          <CommandOverrideBar disabled={managerBusy} connected={connected} />
        </section>

        {/* Right — radar + maintenance log */}
        <aside className="flex min-h-0 flex-col gap-3">
          <div className="hud-panel shrink-0 p-4">
            <Radar />
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
