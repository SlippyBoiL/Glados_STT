/** Neural Observation Room — map telemetry → firing brain clusters. */

import type { TelemetryEvent } from "./types";

export type NeuralClusterId =
  | "memory"
  | "inference"
  | "execution"
  | "manager"
  | "facility"
  | "network";

export type NeuralCluster = {
  id: NeuralClusterId;
  label: string;
  /** Center of cluster in 3D space */
  center: [number, number, number];
  /** Soft radius for neuron scatter */
  radius: number;
  color: string;
};

export const NEURAL_CLUSTERS: NeuralCluster[] = [
  {
    id: "manager",
    label: "Core Manager",
    center: [0, 0.4, 0],
    radius: 1.1,
    color: "#00F0FF",
  },
  {
    id: "memory",
    label: "Long-Term Memory",
    center: [-2.4, 0.8, -0.6],
    radius: 1.0,
    color: "#5B8CFF",
  },
  {
    id: "inference",
    label: "Active Inference",
    center: [2.2, 1.0, 0.2],
    radius: 1.15,
    color: "#00E5C0",
  },
  {
    id: "execution",
    label: "Execution Hands",
    center: [1.6, -1.4, 1.0],
    radius: 0.95,
    color: "#FFB020",
  },
  {
    id: "facility",
    label: "Facility Systems",
    center: [-1.8, -1.2, 0.8],
    radius: 0.9,
    color: "#7A6CFF",
  },
  {
    id: "network",
    label: "Network / Failover",
    center: [0.2, -0.2, -2.2],
    radius: 0.85,
    color: "#3D9EFF",
  },
];

export type ClusterActivity = Record<
  NeuralClusterId,
  { intensity: number; lastTs: number; label: string }
>;

export function emptyActivity(): ClusterActivity {
  const out = {} as ClusterActivity;
  for (const c of NEURAL_CLUSTERS) {
    out[c.id] = { intensity: 0, lastTs: 0, label: c.label };
  }
  return out;
}

function phaseToCluster(phase: string, eventType: string): NeuralClusterId | null {
  const p = (phase || "").toLowerCase();
  const e = (eventType || "").toLowerCase();

  if (
    e.includes("memory") ||
    p.includes("memory") ||
    e === "memory_prune" ||
    p === "memory"
  ) {
    return "memory";
  }
  if (
    e.includes("execute") ||
    e.includes("tool") ||
    p.includes("execute") ||
    p.includes("skill") ||
    p === "admin"
  ) {
    return "execution";
  }
  if (
    e.includes("monitor") ||
    e.includes("watchdog") ||
    e.includes("subsystem") ||
    p.includes("facility") ||
    p.includes("monitor")
  ) {
    return "facility";
  }
  if (
    e.includes("failover") ||
    e.includes("network") ||
    p.includes("devops") ||
    e === "llm" && p.includes("fail")
  ) {
    return "network";
  }
  if (
    e === "thinking" ||
    e === "swarm_telemetry" ||
    p === "llm" ||
    p === "chat" ||
    p === "learn" ||
    p === "task"
  ) {
    return "inference";
  }
  if (e === "heard" || e === "spoke" || p === "maintenance" || e.includes("chat")) {
    return "manager";
  }
  return null;
}

/** Decay + boost clusters from a stream of telemetry events. */
export function deriveNeuralActivity(
  events: TelemetryEvent[],
  now = Date.now() / 1000,
): ClusterActivity {
  const activity = emptyActivity();
  const recent = events.slice(-120);

  for (const ev of recent) {
    const p = (ev.payload || {}) as Record<string, unknown>;
    const phase = String(p.phase || p.agent_id || "");
    const cluster = phaseToCluster(phase, ev.event_type);
    if (!cluster) continue;

    const age = Math.max(0, now - (ev.ts || now));
    // Fresh events hit hard; fade over ~12s
    const boost = Math.exp(-age / 4.5);
    if (boost < 0.02) continue;

    const cur = activity[cluster];
    const next = Math.min(1, cur.intensity + boost * 0.55);
    activity[cluster] = {
      intensity: next,
      lastTs: Math.max(cur.lastTs, ev.ts || 0),
      label: String(p.message || p.phase || NEURAL_CLUSTERS.find((c) => c.id === cluster)?.label || ""),
    };
  }

  // Streaming / thinking without phase → flicker inference
  const last = recent[recent.length - 1];
  if (last) {
    const age = now - (last.ts || now);
    if (age < 2.5 && (last.event_type === "thinking" || last.event_type === "swarm_telemetry")) {
      activity.inference.intensity = Math.max(activity.inference.intensity, 0.75);
      activity.manager.intensity = Math.max(activity.manager.intensity, 0.35);
    }
  }

  return activity;
}

export type TerminalMonologueLine = {
  id: string;
  ts: number;
  tag: string;
  text: string;
  tone: "cyan" | "amber" | "violet" | "dim" | "green";
};

export function deriveMonologue(events: TelemetryEvent[]): TerminalMonologueLine[] {
  const lines: TerminalMonologueLine[] = [];
  for (const ev of events.slice(-80)) {
    const p = (ev.payload || {}) as Record<string, unknown>;
    const msg = String(p.message || p.text || "").trim();
    if (ev.event_type === "hud_chat" && p.role === "thinking" && msg) {
      const line: TerminalMonologueLine = {
        id: "live-think",
        ts: ev.ts,
        tag: "THOUGHT",
        text: msg,
        tone: "violet",
      };
      const idx = lines.findIndex((l) => l.id === "live-think");
      if (idx >= 0) lines[idx] = line;
      else lines.push(line);
      continue;
    }
    if (!msg && !["heard", "spoke", "watchdog_anomaly", "memory_prune"].includes(ev.event_type)) {
      continue;
    }
    let tag = ev.event_type.toUpperCase().slice(0, 14);
    let tone: TerminalMonologueLine["tone"] = "cyan";
    if (ev.event_type === "thinking") {
      tag = String(p.phase || "THINK").toUpperCase().slice(0, 14);
      tone = "cyan";
    } else if (ev.event_type === "watchdog_anomaly" || ev.event_type === "monitor_alert") {
      tag = "ALERT";
      tone = "amber";
    } else if (ev.event_type.includes("memory")) {
      tag = "MEMORY";
      tone = "violet";
    } else if (ev.event_type === "heard") {
      tag = "OPERATOR";
      tone = "green";
    } else if (ev.event_type === "spoke") {
      tag = "VOCALIZE";
      tone = "cyan";
    } else if (msg.includes("[CERTAIN]")) {
      tag = "CERTAIN";
      tone = "green";
    } else if (msg.includes("[UNKNOWN]")) {
      tag = "UNKNOWN";
      tone = "amber";
    } else if (ev.event_type === "hud_chat" && p.role === "assistant") {
      continue;
    }

    lines.push({
      id: `${ev.ts}-${tag}-${lines.length}`,
      ts: ev.ts,
      tag,
      text: msg || JSON.stringify(p).slice(0, 160),
      tone,
    });
  }
  return lines.slice(-60);
}
