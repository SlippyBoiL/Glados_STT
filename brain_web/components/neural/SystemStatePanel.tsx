"use client";

import { motion } from "framer-motion";
import { MetricBar } from "@/components/hud/MetricBar";
import { NEURAL_CLUSTERS, type ClusterActivity } from "@/lib/neuralState";
import type { SystemMetrics } from "@/lib/api";
import type { SwarmDashboardState } from "@/lib/types";

export function SystemStatePanel({
  metrics,
  swarm,
  activity,
  connected,
  endpoints,
}: {
  metrics: SystemMetrics | null;
  swarm: SwarmDashboardState;
  activity: ClusterActivity;
  connected: boolean;
  endpoints?: { name: string; kind: string; ok?: boolean }[];
}) {
  const netTotal =
    (metrics?.network_sent_kbps || 0) + (metrics?.network_recv_kbps || 0);
  const netPct = Math.min(100, netTotal / 50);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="jarvis-glass flex-1 p-4"
      >
        <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.32em] text-[#00F0FF]/80">
          System State
        </p>
        <p className="mb-4 font-mono text-[9px] text-[#00F0FF]/35">
          Host vitals · container watch · API failover lattice
        </p>

        <div className="mb-3 flex items-center gap-2 font-mono text-[10px]">
          <span
            className={
              connected
                ? "text-emerald-400 drop-shadow-[0_0_6px_rgba(52,211,153,0.6)]"
                : "text-red-400"
            }
          >
            {connected ? "● TELEMETRY LINKED" : "○ LINK DOWN"}
          </span>
          <span className="text-[#00F0FF]/30">{metrics?.hostname || "—"}</span>
        </div>

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

        <div className="mt-5 border-t border-[#00F0FF]/10 pt-3">
          <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-[#00F0FF]/50">
            Cognitive clusters
          </p>
          <ul className="space-y-1.5">
            {NEURAL_CLUSTERS.map((c) => {
              const inten = activity[c.id]?.intensity || 0;
              return (
                <li key={c.id} className="font-mono text-[10px]">
                  <div className="mb-0.5 flex justify-between text-[#00F0FF]/70">
                    <span>{c.label}</span>
                    <span>{Math.round(inten * 100)}%</span>
                  </div>
                  <div className="h-1 overflow-hidden rounded-full bg-[#001220]">
                    <motion.div
                      className="h-full rounded-full"
                      style={{
                        background: `linear-gradient(90deg, ${c.color}88, ${c.color})`,
                        boxShadow: inten > 0.2 ? `0 0 8px ${c.color}` : undefined,
                      }}
                      animate={{ width: `${Math.round(inten * 100)}%` }}
                      transition={{ type: "spring", stiffness: 120, damping: 20 }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="mt-5 border-t border-[#00F0FF]/10 pt-3">
          <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-[#00F0FF]/50">
            API failover nodes
          </p>
          <ul className="space-y-1 font-mono text-[10px] text-[#00F0FF]/65">
            {(endpoints && endpoints.length
              ? endpoints
              : [
                  { name: "nvidia-1", kind: "nvidia", ok: true },
                  { name: "nvidia-2", kind: "nvidia", ok: true },
                  { name: "nvidia-3", kind: "nvidia", ok: true },
                  { name: "local-deepseek-moe", kind: "local", ok: true },
                ]
            ).map((ep) => (
              <li key={ep.name} className="flex items-center gap-2">
                <span
                  className={
                    ep.ok === false ? "text-red-400" : "text-emerald-400"
                  }
                >
                  ●
                </span>
                <span>{ep.name}</span>
                <span className="text-[#00F0FF]/30">{ep.kind}</span>
              </li>
            ))}
          </ul>
        </div>

        {swarm.services?.length > 0 && (
          <div className="mt-5 border-t border-[#00F0FF]/10 pt-3">
            <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-[#00F0FF]/50">
              Facility services
            </p>
            <ul className="max-h-28 space-y-1 overflow-y-auto font-mono text-[10px]">
              {swarm.services.map((s) => (
                <li key={s.id} className="flex justify-between text-[#00F0FF]/65">
                  <span>{s.name}</span>
                  <span className={s.ok ? "text-emerald-400" : "text-amber-400"}>
                    {s.ok ? "OK" : "ALERT"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </motion.div>
    </div>
  );
}
