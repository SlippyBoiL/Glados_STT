"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { JarvisOrb } from "@/components/hud/JarvisOrb";
import { MetricBar } from "@/components/hud/MetricBar";
import { Radar } from "@/components/hud/Radar";
import { TelemetryPanel } from "@/components/hud/TelemetryPanel";
import { HudChat } from "@/components/hud/HudChat";
import { ThoughtProcess } from "@/components/hud/ThoughtProcess";
import { Waveform } from "@/components/hud/Waveform";
import { api, type SystemMetrics } from "@/lib/api";
import { deriveVoiceState, lastSubtitle } from "@/lib/hudState";
import { useLiveTelemetry } from "@/lib/ws";
import type { BrainState } from "@/lib/types";

export default function CommandCenterPage() {
  const { events, connected } = useLiveTelemetry(300);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [state, setState] = useState<BrainState | null>(null);
  const voiceState = deriveVoiceState(events);
  const subtitle = lastSubtitle(events);

  useEffect(() => {
    const load = () => {
      api.metrics().then(setMetrics).catch(() => {});
      api.state().then(setState).catch(() => {});
    };
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, []);

  const netTotal =
    (metrics?.network_sent_kbps || 0) + (metrics?.network_recv_kbps || 0);
  const netPct = Math.min(100, netTotal / 50);

  return (
    <div className="hud-root relative min-h-screen overflow-hidden bg-hud-bg text-hud-cyan">
      <div className="hud-grid pointer-events-none absolute inset-0" />

      {/* Header */}
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
            {connected ? "● LINKED" : "○ OFFLINE"}
          </span>
          <span className="text-hud-cyan/40">{metrics?.hostname || "—"}</span>
          <Link
            href="/"
            className="rounded border border-hud-cyan/20 px-2 py-1 text-hud-cyan/60 hover:text-hud-cyan"
          >
            Observatory
          </Link>
        </div>
      </header>

      {/* Main grid */}
      <div className="relative z-10 grid min-h-[calc(100vh-56px)] grid-cols-12 gap-3 p-4">
        {/* Left column */}
        <aside className="col-span-12 flex flex-col gap-3 lg:col-span-3">
          <div className="hud-panel p-4">
            <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
              System Metrics
            </p>
            <MetricBar
              label="CPU"
              value={metrics?.cpu_percent ?? 0}
            />
            <MetricBar
              label="RAM"
              value={metrics?.ram_percent ?? 0}
              detail={
                metrics
                  ? `${metrics.ram_used_gb}/${metrics.ram_total_gb} GB`
                  : undefined
              }
            />
            <MetricBar
              label="Disk"
              value={metrics?.disk_percent ?? 0}
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
          <div className="min-h-[180px] flex-1 lg:min-h-[240px]">
            <ThoughtProcess events={events} />
          </div>
          <div className="min-h-[140px] lg:min-h-[160px]">
            <TelemetryPanel events={events} />
          </div>
        </aside>

        {/* Center */}
        <section className="col-span-12 flex min-h-0 flex-col lg:col-span-6">
          <JarvisOrb voiceState={voiceState} />
          <div className="hud-panel mx-auto mt-2 max-w-2xl px-6 py-3 text-center">
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-hud-cyan/50">
              Latest output
            </p>
            <p className="mt-2 text-sm leading-relaxed text-hud-cyan/90 md:text-base">
              {subtitle}
            </p>
          </div>
          <div className="mx-auto mt-3 w-full max-w-2xl shrink-0">
            <HudChat events={events} />
          </div>
          <div className="hud-panel mt-3 p-2">
            <Waveform voiceState={voiceState} />
          </div>
        </section>

        {/* Right column */}
        <aside className="col-span-12 flex flex-col gap-3 lg:col-span-3">
          <div className="hud-panel p-4">
            <Radar />
          </div>
          <div className="hud-panel flex-1 p-4 font-mono text-[10px]">
            <p className="mb-2 uppercase tracking-[0.2em] text-hud-cyan">
              Subsystems
            </p>
            <ul className="space-y-2 text-hud-cyan/60">
              <li className="flex justify-between">
                <span>Vision</span>
                <span
                  className={
                    state?.subsystem_flags?.vision_enabled
                      ? "text-emerald-400"
                      : "text-red-400"
                  }
                >
                  {state?.subsystem_flags?.vision_enabled ? "ON" : "OFF"}
                </span>
              </li>
              <li className="flex justify-between">
                <span>Monitoring</span>
                <span
                  className={
                    state?.subsystem_flags?.monitoring_enabled
                      ? "text-emerald-400"
                      : "text-red-400"
                  }
                >
                  {state?.subsystem_flags?.monitoring_enabled ? "ON" : "OFF"}
                </span>
              </li>
              <li className="flex justify-between">
                <span>Events</span>
                <span>{state?.event_count ?? "—"}</span>
              </li>
            </ul>
            {state?.last_intent ? (
              <div className="mt-4 border-t border-hud-cyan/10 pt-3">
                <p className="text-hud-cyan/40">Last intent</p>
                <p className="text-hud-cyan/80">
                  {String(state.last_intent.category)} ·{" "}
                  {Number(state.last_intent.confidence).toFixed(0)}%
                </p>
              </div>
            ) : null}
            {state?.last_skills_matched?.skills?.length ? (
              <div className="mt-3 border-t border-hud-cyan/10 pt-3">
                <p className="text-hud-cyan/40">Protocols</p>
                {state.last_skills_matched.skills.slice(0, 3).map((s) => (
                  <p key={s.file} className="truncate text-hud-cyan/70">
                    {s.file}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        </aside>
      </div>

      <footer className="relative z-10 border-t border-hud-cyan/10 py-2 text-center font-mono text-[9px] uppercase tracking-[0.4em] text-hud-cyan/30">
        For science · Fullscreen recommended (F11)
      </footer>
    </div>
  );
}
