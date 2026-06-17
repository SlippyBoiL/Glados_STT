"use client";

import { motion } from "framer-motion";
import { SWARM_ROSTER } from "@/lib/swarmState";
import type { SwarmAgentId, SwarmDashboardState } from "@/lib/types";

const NODE_POSITIONS: Record<SwarmAgentId, { x: number; y: number }> = {
  MANAGER: { x: 200, y: 60 },
  CORE_CODER: { x: 80, y: 140 },
  WEB_RESEARCHER: { x: 320, y: 140 },
  QA_FACT_CHECKER: { x: 80, y: 240 },
  DEVOPS_OVERSEER: { x: 320, y: 240 },
  FACILITY_MANAGER: { x: 140, y: 320 },
  MAINTENANCE_AGENT: { x: 260, y: 320 },
};

type Props = {
  swarm: SwarmDashboardState;
};

export function SwarmNetworkCanvas({ swarm }: Props) {
  const hub = NODE_POSITIONS.MANAGER;
  const brainActive =
    swarm.brainWriteNonce > 0 &&
    Date.now() / 1000 - swarm.lastBrainWriteTs < 4;

  return (
    <div className="panel relative flex h-full min-h-[280px] flex-col p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs uppercase tracking-widest text-aperture-muted">
          Agent Network
        </p>
        <span
          className={`text-[10px] font-mono transition-colors ${
            brainActive
              ? "animate-pulse text-aperture-orange"
              : "text-aperture-muted"
          }`}
        >
          {brainActive ? "● CENTRAL BRAIN WRITING" : "○ Central brain idle"}
        </span>
      </div>
      {brainActive ? (
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-lg bg-aperture-orange/10"
          animate={{ opacity: [0.2, 0.55, 0.2] }}
          transition={{ duration: 0.8, repeat: 3 }}
          key={swarm.brainWriteNonce}
        />
      ) : null}
      <svg viewBox="0 0 400 380" className="relative h-full w-full flex-1">
        {SWARM_ROSTER.filter((a) => a.id !== "MANAGER").map(({ id }) => {
          const pos = NODE_POSITIONS[id];
          return (
            <line
              key={`link-${id}`}
              x1={hub.x}
              y1={hub.y}
              x2={pos.x}
              y2={pos.y}
              stroke="rgba(74, 127, 165, 0.25)"
              strokeWidth={1}
            />
          );
        })}
        {SWARM_ROSTER.map(({ id, name }) => {
          const pos = NODE_POSITIONS[id];
          const agent = swarm.agents[id];
          const active = swarm.lastPulseAgent === id;
          const brainHub = id === "MANAGER" && brainActive;
          const fill =
            brainHub
              ? "rgba(193, 122, 58, 0.65)"
              : agent.status === "alert"
              ? "rgba(239, 68, 68, 0.5)"
              : agent.status === "thinking" || agent.status === "recovering"
                ? "rgba(251, 191, 36, 0.45)"
                : "rgba(74, 127, 165, 0.35)";

          return (
            <g key={id}>
              <motion.circle
                cx={pos.x}
                cy={pos.y}
                r={brainHub ? 26 : active ? 22 : 18}
                fill={fill}
                stroke={brainHub || active ? "#c17a3a" : "#4a7fa5"}
                strokeWidth={brainHub || active ? 2.5 : 1.5}
                animate={
                  brainHub
                    ? { scale: [1, 1.25, 1], opacity: [0.6, 1, 0.6] }
                    : active
                    ? { scale: [1, 1.15, 1], opacity: [0.7, 1, 0.7] }
                    : { scale: 1, opacity: 0.85 }
                }
                transition={{ duration: 0.6, repeat: brainHub ? 4 : active ? 2 : 0 }}
                key={`${id}-${agent.pulseKey}-${swarm.brainWriteNonce}`}
              />
              <text
                x={pos.x}
                y={pos.y + 34}
                textAnchor="middle"
                fill="#6b7585"
                fontSize="8"
                fontFamily="monospace"
              >
                {name.split(" ")[0]}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
