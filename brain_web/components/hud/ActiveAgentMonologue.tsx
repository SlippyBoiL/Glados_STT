"use client";

import { useEffect, useRef } from "react";
import { AGENT_TAG } from "@/lib/swarmState";
import type { SwarmAgentId, SwarmDashboardState } from "@/lib/types";

type Props = {
  swarm: SwarmDashboardState;
};

export function ActiveAgentMonologue({ swarm }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const activeTag = swarm.activeAgentId
    ? AGENT_TAG[swarm.activeAgentId as SwarmAgentId]
    : null;

  const rows = swarm.terminalLog;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rows.length, swarm.agentMonologue.length]);

  return (
    <div className="hud-panel flex min-h-[200px] flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-hud-cyan/10 px-3 py-2">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
          Active Agent Monologue
        </p>
        {activeTag ? (
          <span className="animate-pulse font-mono text-[10px] text-amber-300">
            ● {activeTag}
          </span>
        ) : (
          <span className="font-mono text-[10px] text-hud-cyan/40">idle</span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto bg-black/50 p-3 font-mono text-[11px] leading-relaxed">
        {rows.length === 0 && swarm.agentMonologue.length === 0 ? (
          <p className="text-hud-cyan/40">
            Awaiting swarm telemetry… agent logs stream here with [AGENT_ID] prefixes.
          </p>
        ) : (
          <>
            {swarm.agentMonologue.map((line, i) => (
              <div
                key={`a-${i}-${line.slice(0, 20)}`}
                className="whitespace-pre-wrap text-hud-cyan/85"
              >
                {line}
              </div>
            ))}
            {rows.map((row) => {
              if (row.kind === "tool_intent") {
                return (
                  <div
                    key={row.id}
                    className="whitespace-pre-wrap text-amber-400"
                  >
                    {row.text}
                  </div>
                );
              }
              if (row.kind === "tool_result") {
                return (
                  <div
                    key={row.id}
                    className="whitespace-pre-wrap pl-2 text-gray-400"
                  >
                    {row.text}
                  </div>
                );
              }
              return null;
            })}
          </>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
