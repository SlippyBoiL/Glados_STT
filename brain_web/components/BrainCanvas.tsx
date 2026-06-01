"use client";

import { motion } from "framer-motion";

type Region = "idle" | "hearing" | "memory" | "intent" | "reason" | "action";

const regionMap: Record<string, Region> = {
  heard: "hearing",
  memory_retrieved: "memory",
  intent_classified: "intent",
  llm_response: "reason",
  cursor_prompt: "reason",
  skills_matched: "intent",
  code_executed: "action",
  monitor_alert: "action",
  subsystem_status: "memory",
};

type Props = {
  activeEventType?: string;
};

export function BrainCanvas({ activeEventType }: Props) {
  const region = activeEventType
    ? regionMap[activeEventType] || "idle"
    : "idle";

  const pulse = (name: Region, cx: number, cy: number, r: number) => {
    const on = region === name;
    return (
      <motion.circle
        key={name}
        cx={cx}
        cy={cy}
        r={r}
        fill={on ? "rgba(193, 122, 58, 0.35)" : "rgba(42, 49, 64, 0.5)"}
        stroke={on ? "#c17a3a" : "#2a3140"}
        strokeWidth={on ? 2 : 1}
        animate={on ? { opacity: [0.5, 1, 0.5] } : { opacity: 0.4 }}
        transition={{ duration: 1.2, repeat: on ? Infinity : 0 }}
      />
    );
  };

  return (
    <div className="panel flex h-full min-h-[320px] flex-col items-center justify-center p-4">
      <p className="mb-3 text-xs uppercase tracking-widest text-aperture-muted">
        Neural Activity
      </p>
      <svg viewBox="0 0 200 220" className="h-64 w-full max-w-xs">
        <ellipse
          cx="100"
          cy="110"
          rx="78"
          ry="88"
          fill="rgba(21, 25, 32, 0.9)"
          stroke="#2a3140"
          strokeWidth="2"
        />
        {pulse("hearing", 100, 45, 18)}
        {pulse("memory", 55, 95, 16)}
        {pulse("intent", 145, 95, 16)}
        {pulse("reason", 100, 120, 22)}
        {pulse("action", 100, 175, 14)}
        <text
          x="100"
          y="215"
          textAnchor="middle"
          fill="#6b7585"
          fontSize="9"
          fontFamily="monospace"
        >
          {region === "idle" ? "STANDBY" : region.toUpperCase()}
        </text>
      </svg>
      <div className="mt-2 grid w-full grid-cols-3 gap-1 text-[10px] text-aperture-muted">
        {(["hearing", "memory", "intent", "reason", "action"] as Region[]).map(
          (r) => (
            <span
              key={r}
              className={region === r ? "text-aperture-orange" : ""}
            >
              {r}
            </span>
          ),
        )}
      </div>
    </div>
  );
}
