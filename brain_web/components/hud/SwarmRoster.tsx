"use client";

import {
  AGENT_TAG,
  hudStatusAnimation,
  hudStatusColor,
  SWARM_ROSTER,
} from "@/lib/swarmState";
import type { SwarmAgentId, SwarmDashboardState } from "@/lib/types";

type Props = {
  swarm: SwarmDashboardState;
};

export function SwarmRoster({ swarm }: Props) {
  return (
    <div className="hud-panel flex min-h-0 flex-1 flex-col overflow-hidden p-3">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
        Swarm Roster
      </p>
      <ul className="flex-1 space-y-1.5 overflow-y-auto">
        {SWARM_ROSTER.map(({ id, name }) => {
          const agent = swarm.agents[id];
          const highlighted =
            swarm.activeAgentId === id ||
            agent.status === "thinking" ||
            agent.status === "recovering" ||
            agent.status === "alert";
          return (
            <li
              key={id}
              className={`rounded border px-2.5 py-2 transition-colors ${
                highlighted
                  ? "border-hud-cyan/50 bg-hud-cyan/5 shadow-[0_0_12px_rgba(61,214,255,0.12)]"
                  : "border-hud-cyan/10 bg-hud-bg/40"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-block h-2 w-2 shrink-0 rounded-full ${hudStatusColor(agent.status)} ${hudStatusAnimation(agent.status)}`}
                  title={agent.status}
                />
                <span className="truncate text-xs text-hud-cyan/90">{name}</span>
                <span className="ml-auto font-mono text-[9px] text-hud-cyan/40">
                  {AGENT_TAG[id]}
                </span>
              </div>
              <p className="mt-1 truncate pl-4 font-mono text-[10px] text-hud-cyan/50">
                {agent.currentSubtask || "Standing by"}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
