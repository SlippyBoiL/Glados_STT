"use client";

import {
  statusAnimation,
  statusColor,
  SWARM_ROSTER,
} from "@/lib/swarmState";
import type { SwarmDashboardState } from "@/lib/types";

type Props = {
  swarm: SwarmDashboardState;
};

export function SwarmRosterPanel({ swarm }: Props) {
  return (
    <div className="panel flex h-full flex-col p-3">
      <p className="mb-3 text-xs uppercase tracking-widest text-aperture-muted">
        Swarm Roster
      </p>
      <ul className="flex-1 space-y-2 overflow-y-auto">
        {SWARM_ROSTER.map(({ id, name }) => {
          const agent = swarm.agents[id];
          return (
            <li
              key={id}
              className="rounded border border-aperture-border/80 bg-aperture-bg/40 px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${statusColor(agent.status)} ${statusAnimation(agent.status)}`}
                  title={agent.status}
                />
                <span className="text-sm font-medium text-aperture-text">{name}</span>
              </div>
              <p className="mt-1 truncate pl-5 text-[11px] text-aperture-muted">
                {agent.currentSubtask || "Standing by"}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
