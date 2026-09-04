"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { InternalMonologue } from "@/components/swarm/InternalMonologue";
import { MaintenanceLog } from "@/components/swarm/MaintenanceLog";
import { SwarmNetworkCanvas } from "@/components/swarm/SwarmNetworkCanvas";
import { SwarmRosterPanel } from "@/components/swarm/SwarmRosterPanel";
import { SwarmTaskConsole } from "@/components/swarm/SwarmTaskConsole";
import { TelemetrySidebar } from "@/components/swarm/TelemetrySidebar";
import { api } from "@/lib/api";
import { buildSwarmState } from "@/lib/swarmState";
import { useLiveTelemetry } from "@/lib/ws";
import type { SwarmDashboardState } from "@/lib/types";

export default function SwarmObservatoryPage() {
  const { events, connected } = useLiveTelemetry(500);
  const [swarm, setSwarm] = useState<SwarmDashboardState>(() =>
    buildSwarmState([]),
  );

  useEffect(() => {
    setSwarm(buildSwarmState(events));
  }, [events]);

  useEffect(() => {
    const poll = () => {
      api.metrics().then((m) => {
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
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold">Swarm Observatory</h2>
          <p className="text-sm text-aperture-muted">
            Seven-agent telemetry — roster, network, vitals, and maintenance
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/"
            className="rounded border border-aperture-orange/50 px-3 py-1.5 text-xs text-aperture-orange hover:bg-aperture-orange/10"
          >
            ← Command Center
          </Link>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-12">
        <aside className="lg:col-span-3">
          <SwarmRosterPanel swarm={swarm} />
        </aside>

        <section className="flex min-h-0 flex-col gap-3 lg:col-span-6">
          <div className="min-h-[280px] flex-1">
            <SwarmNetworkCanvas swarm={swarm} />
          </div>
          <InternalMonologue terminalLog={swarm.terminalLog} />
        </section>

        <aside className="flex min-h-0 flex-col gap-3 lg:col-span-3">
          <TelemetrySidebar swarm={swarm} connected={connected} />
          <MaintenanceLog lines={swarm.maintenanceLog} />
        </aside>
      </div>

      <SwarmTaskConsole events={events} />
    </div>
  );
}
