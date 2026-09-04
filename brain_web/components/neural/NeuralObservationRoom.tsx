"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { NeuralBrainViewport } from "@/components/neural/NeuralBrainViewport";
import { SystemStatePanel } from "@/components/neural/SystemStatePanel";
import { LiveChatPanel } from "@/components/neural/LiveChatPanel";
import { api, type SystemMetrics } from "@/lib/api";
import {
  deriveNeuralActivity,
  emptyActivity,
} from "@/lib/neuralState";
import { buildSwarmState } from "@/lib/swarmState";
import { useLiveTelemetry } from "@/lib/ws";
import type { SwarmDashboardState } from "@/lib/types";

/** GLaDOS Neural Observation Room — JARVIS holographic + Aperture admin terminal. */
export function NeuralObservationRoom() {
  const { events, connected } = useLiveTelemetry(500);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [swarm, setSwarm] = useState<SwarmDashboardState>(() =>
    buildSwarmState([]),
  );
  const [now, setNow] = useState(() => Date.now() / 1000);

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

  // Tick so neural intensities decay smoothly
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now() / 1000), 200);
    return () => clearInterval(t);
  }, []);

  const activity = useMemo(
    () => (events.length ? deriveNeuralActivity(events, now) : emptyActivity()),
    [events, now],
  );

  const activeLabel = useMemo(() => {
    let best = { id: "", intensity: 0, label: "Idle" };
    for (const [id, v] of Object.entries(activity)) {
      if (v.intensity > best.intensity) {
        best = { id, intensity: v.intensity, label: v.label || id };
      }
    }
    return best.intensity > 0.15 ? best.label : "Standby — awaiting directive";
  }, [activity]);

  return (
    <div className="neural-root relative min-h-screen overflow-hidden bg-[#00050b] text-[#00F0FF]">
      <div className="neural-grid pointer-events-none absolute inset-0" />
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(ellipse at 50% 0%, rgba(0,240,255,0.12) 0%, transparent 50%), radial-gradient(ellipse at 80% 100%, rgba(30,80,180,0.15) 0%, transparent 45%)",
        }}
      />

      <header className="relative z-10 flex items-center justify-between border-b border-[#00F0FF]/15 px-6 py-3 backdrop-blur-md">
        <div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-mono text-[10px] uppercase tracking-[0.45em] text-[#00F0FF]/55"
          >
            Aperture Science · Neural Observation Room
          </motion.p>
          <h1 className="mt-0.5 text-lg font-light tracking-[0.18em] text-[#00F0FF] md:text-xl">
            G.L.a.D.O.S. ADMINISTRATIVE TERMINAL
          </h1>
        </div>
        <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-[0.2em]">
          <span className="hidden text-[#00F0FF]/40 md:inline truncate max-w-[280px] normal-case tracking-normal">
            {activeLabel}
          </span>
          <span className={connected ? "text-emerald-400" : "text-red-400"}>
            {connected ? "● LINKED" : "○ OFFLINE"}
          </span>
          <Link
            href="/observatory/"
            className="border border-[#00F0FF]/25 px-2 py-1 text-[#00F0FF]/60 transition hover:border-[#00F0FF]/60 hover:text-[#00F0FF]"
          >
            Observatory
          </Link>
          <Link
            href="/hud/"
            className="border border-[#00F0FF]/15 px-2 py-1 text-[#00F0FF]/40 transition hover:text-[#00F0FF]/80"
          >
            Legacy HUD
          </Link>
        </div>
      </header>

      <div className="relative z-10 grid h-[calc(100vh-60px)] grid-cols-1 gap-3 overflow-hidden p-3 lg:grid-cols-[minmax(0,26fr)_minmax(0,48fr)_minmax(0,26fr)]">
        <aside className="min-h-0 overflow-hidden">
          <SystemStatePanel
            metrics={metrics}
            swarm={swarm}
            activity={activity}
            connected={connected}
          />
        </aside>

        <section className="flex min-h-0 flex-col gap-2 overflow-hidden">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex shrink-0 items-center justify-between px-1"
          >
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#00F0FF]/70">
              Live Firing Brain
            </p>
            <p className="font-mono text-[9px] text-[#00F0FF]/35">
              Clusters ignite from WebSocket telemetry
            </p>
          </motion.div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <NeuralBrainViewport activity={activity} />
          </div>
        </section>

        <aside className="min-h-0 overflow-hidden">
          <LiveChatPanel events={events} />
        </aside>
      </div>
    </div>
  );
}
