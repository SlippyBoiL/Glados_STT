import type {
  SwarmAgentId,
  SwarmAgentState,
  SwarmAgentStatus,
  SwarmDashboardState,
  TelemetryEvent,
} from "./types";

export const SWARM_ROSTER: { id: SwarmAgentId; name: string }[] = [
  { id: "MANAGER", name: "GLaDOS (Core Manager)" },
  { id: "CORE_CODER", name: "Core Coder" },
  { id: "WEB_RESEARCHER", name: "Web Researcher" },
  { id: "QA_FACT_CHECKER", name: "QA & Fact-Checker" },
  { id: "DEVOPS_OVERSEER", name: "DevOps Overseer" },
  { id: "FACILITY_MANAGER", name: "Facility Manager" },
  { id: "MAINTENANCE_AGENT", name: "Reliability Maintenance" },
];

/** Short tags shown in the Active Agent Monologue terminal. */
export const AGENT_TAG: Record<SwarmAgentId, string> = {
  MANAGER: "MANAGER",
  CORE_CODER: "CODER",
  WEB_RESEARCHER: "RESEARCHER",
  QA_FACT_CHECKER: "QA",
  DEVOPS_OVERSEER: "DEVOPS",
  FACILITY_MANAGER: "FACILITY",
  MAINTENANCE_AGENT: "MAINTENANCE",
};

const AGENT_ID_ALIASES: Record<string, SwarmAgentId> = {
  MANAGER: "MANAGER",
  CORE_CODER: "CORE_CODER",
  CODER: "CORE_CODER",
  WEB_RESEARCHER: "WEB_RESEARCHER",
  RESEARCHER: "WEB_RESEARCHER",
  QA_FACT_CHECKER: "QA_FACT_CHECKER",
  QA: "QA_FACT_CHECKER",
  FACT_CHECKER: "QA_FACT_CHECKER",
  DEVOPS_OVERSEER: "DEVOPS_OVERSEER",
  DEVOPS: "DEVOPS_OVERSEER",
  FACILITY_MANAGER: "FACILITY_MANAGER",
  FACILITY: "FACILITY_MANAGER",
  MAINTENANCE_AGENT: "MAINTENANCE_AGENT",
  MAINTENANCE: "MAINTENANCE_AGENT",
};

const PHASE_AGENT: Record<string, SwarmAgentId> = {
  facility: "FACILITY_MANAGER",
  browser: "WEB_RESEARCHER",
  learn: "WEB_RESEARCHER",
  task: "CORE_CODER",
  skills: "CORE_CODER",
  execute: "CORE_CODER",
  llm: "MANAGER",
  memory: "MANAGER",
  chat: "MANAGER",
  admin: "DEVOPS_OVERSEER",
  maintenance: "MAINTENANCE_AGENT",
  monitor: "DEVOPS_OVERSEER",
  intent: "QA_FACT_CHECKER",
};

const DEFAULT_SERVICES = [
  { id: "pihole", name: "Pi-hole DNS" },
  { id: "twingate", name: "Twingate Connector" },
  { id: "raspberry_pi", name: "Raspberry Pi Server" },
  { id: "govee", name: "Govee API Gateway" },
  { id: "autocad", name: "AutoCAD Integration" },
];

function defaultAgents(): Record<SwarmAgentId, SwarmAgentState> {
  const agents = {} as Record<SwarmAgentId, SwarmAgentState>;
  for (const entry of SWARM_ROSTER) {
    agents[entry.id] = {
      id: entry.id,
      name: entry.name,
      status: "idle",
      currentSubtask: "Standing by",
      lastMessage: "",
      lastActiveTs: 0,
      pulseKey: 0,
    };
  }
  return agents;
}

export function initialSwarmState(): SwarmDashboardState {
  return {
    agents: defaultAgents(),
    monologue: [],
    maintenanceLog: [],
    metrics: { cpu: 0, ram: 0, disk: 0 },
    services: DEFAULT_SERVICES.map((s) => ({
      ...s,
      ok: true,
      alerts: [],
      lastTs: 0,
    })),
    lastPulseAgent: null,
    pulseNonce: 0,
    brainWriteNonce: 0,
    lastBrainWriteTs: 0,
    activeAgentId: null,
    agentMonologue: [],
  };
}

export function resolveAgentId(payload: Record<string, unknown>): SwarmAgentId | null {
  const raw = String(payload.agent_id || payload.agent || "")
    .trim()
    .toUpperCase();
  if (!raw) return null;
  const mapped = AGENT_ID_ALIASES[raw];
  if (mapped) return mapped;
  return isAgentId(raw) ? raw : null;
}

function appendAgentMonologue(
  state: SwarmDashboardState,
  agentId: SwarmAgentId,
  message: string,
  max = 250,
): SwarmDashboardState {
  const text = (message || "").trim();
  if (!text) return state;
  const tag = AGENT_TAG[agentId];
  const line = `[${tag}] ${text}`.slice(0, 500);
  return {
    ...state,
    agentMonologue: [...state.agentMonologue, line].slice(-max),
    activeAgentId: agentId,
  };
}

function normalizeStatus(raw: string | undefined): SwarmAgentStatus {
  const s = (raw || "idle").toLowerCase();
  if (s === "error") return "alert";
  if (s === "thinking" || s === "recovering") return s as SwarmAgentStatus;
  if (s === "alert") return "alert";
  return "idle";
}

function isAgentId(id: string): id is SwarmAgentId {
  return SWARM_ROSTER.some((a) => a.id === id);
}

function appendMonologue(state: SwarmDashboardState, line: string, max = 200): string[] {
  const next = [...state.monologue, line];
  return next.slice(-max);
}

function updateAgent(
  state: SwarmDashboardState,
  agentId: SwarmAgentId,
  patch: Partial<SwarmAgentState>,
  pulse = true,
): SwarmDashboardState {
  const prev = state.agents[agentId];
  return {
    ...state,
    agents: {
      ...state.agents,
      [agentId]: {
        ...prev,
        ...patch,
        lastActiveTs: Date.now() / 1000,
        pulseKey: pulse ? prev.pulseKey + 1 : prev.pulseKey,
      },
    },
    lastPulseAgent: pulse ? agentId : state.lastPulseAgent,
    pulseNonce: pulse ? state.pulseNonce + 1 : state.pulseNonce,
  };
}

function formatLogLine(ev: TelemetryEvent): string {
  const ts = new Date(ev.ts * 1000).toLocaleTimeString();
  const p = ev.payload || {};
  const msg =
    String(p.message || p.text || p.output_preview || p.phase || ev.event_type);
  return `[${ts}] ${ev.event_type}: ${msg}`.slice(0, 400);
}

function formatMaintenanceLine(ev: TelemetryEvent): string {
  const p = ev.payload || {};
  const ts = String(p.timestamp || new Date(ev.ts * 1000).toLocaleTimeString());
  const msg = String(p.message || "");
  return `[MAINTENANCE] ${ts} — ${msg}`.slice(0, 400);
}

export function reduceSwarmEvent(
  state: SwarmDashboardState,
  ev: TelemetryEvent,
): SwarmDashboardState {
  let next: SwarmDashboardState = {
    ...state,
    monologue: appendMonologue(state, formatLogLine(ev)),
  };

  const p = ev.payload || {};

  if (ev.event_type === "user_text_prompt") {
    const text = String(p.text || "");
    next = updateAgent(next, "MANAGER", {
      status: "thinking",
      currentSubtask: text.slice(0, 120) || "Manual override",
      lastMessage: text,
    });
    if (text) {
      next = appendAgentMonologue(next, "MANAGER", `Manual override: ${text}`);
    }
    return next;
  }

  if (ev.event_type === "brain_update") {
    const sender = String(p.sender_agent || "MANAGER");
    const agentId = isAgentId(sender) ? sender : "MANAGER";
    const preview = String(p.insight_preview || p.message || "Writing to central brain…");
    next = updateAgent(next, agentId, {
      status: "thinking",
      currentSubtask: "Committing shared insight",
      lastMessage: preview,
    });
    next = appendAgentMonologue(next, agentId, preview);
    return {
      ...next,
      brainWriteNonce: next.brainWriteNonce + 1,
      lastBrainWriteTs: ev.ts,
      monologue: appendMonologue(
        next,
        `[BRAIN] ${String(p.timestamp || "")} ${sender}: ${preview}`,
      ),
    };
  }

  if (ev.event_type === "swarm_telemetry" || ev.event_type === "maintenance_action") {
    const agentId = resolveAgentId(p);
    if (agentId) {
      const status = normalizeStatus(String(p.status || "thinking"));
      const subtask = String(
        p.current_subtask || p.message || next.agents[agentId].currentSubtask,
      );
      const msg = String(p.message || subtask);
      next = updateAgent(next, agentId, {
        status,
        currentSubtask: subtask,
        lastMessage: msg,
      });
      if (msg && (status === "thinking" || status === "recovering" || status === "alert")) {
        next = appendAgentMonologue(next, agentId, msg);
      }
    }
    if (ev.event_type === "maintenance_action") {
      next = {
        ...next,
        maintenanceLog: [...next.maintenanceLog, formatMaintenanceLine(ev)].slice(-80),
      };
    }
    return next;
  }

  if (ev.event_type === "system_metrics") {
    const m = (p.metrics || p.detail || p) as Record<string, number>;
    return {
      ...next,
      metrics: {
        cpu: Number(m.cpu ?? m.cpu_percent ?? next.metrics.cpu),
        ram: Number(m.ram ?? m.ram_percent ?? next.metrics.ram),
        disk: Number(m.disk ?? m.disk_percent ?? next.metrics.disk),
      },
    };
  }

  if (ev.event_type === "thinking") {
    const phase = String(p.phase || "");
    const agentId = PHASE_AGENT[phase] || "MANAGER";
    const msg = String(p.message || phase);
    next = updateAgent(next, agentId, {
      status: "thinking",
      currentSubtask: msg,
      lastMessage: msg,
    });
    next = appendAgentMonologue(next, agentId, msg);
    return next;
  }

  if (ev.event_type === "monitor_alert") {
    const device = String(p.device || "unknown");
    next = updateAgent(next, "DEVOPS_OVERSEER", {
      status: "alert",
      currentSubtask: `Alert: ${device}`,
      lastMessage: String((p.alerts as string[])?.join(" | ") || device),
    });
    next = appendAgentMonologue(
      next,
      "DEVOPS_OVERSEER",
      `Alert on ${device}: ${String((p.alerts as string[])?.join(" | ") || device)}`,
    );
    next = {
      ...next,
      services: next.services.map((s) =>
        s.id === device || s.name.toLowerCase().includes(device)
          ? {
              ...s,
              ok: false,
              alerts: (p.alerts as string[]) || [],
              lastTs: ev.ts,
            }
          : s,
      ),
    };
    return next;
  }

  if (ev.event_type === "subsystem_status") {
    const device = String(p.device || "");
    const ok = Boolean(p.ok ?? true);
    next = {
      ...next,
      services: next.services.map((s) =>
        s.id === device || (device && s.name.toLowerCase().includes(device))
          ? {
              ...s,
              ok,
              alerts: ok ? [] : (p.alerts as string[]) || s.alerts,
              lastTs: ev.ts,
            }
          : s,
      ),
    };
    if (!ok) {
      next = updateAgent(next, "DEVOPS_OVERSEER", {
        status: "alert",
        currentSubtask: `${device} degraded`,
      });
    }
    return next;
  }

  const eventAgentMap: Record<string, SwarmAgentId> = {
    facility_brain: "FACILITY_MANAGER",
    facility_scan: "FACILITY_MANAGER",
    skills_matched: "CORE_CODER",
    skill_learned: "CORE_CODER",
    code_executed: "CORE_CODER",
    browser_step: "WEB_RESEARCHER",
    intent_classified: "QA_FACT_CHECKER",
    llm_response: "MANAGER",
    heard: "MANAGER",
  };

  const mapped = eventAgentMap[ev.event_type];
  if (mapped) {
    const idleAfter = ["llm_response", "code_executed", "facility_brain"];
    const msg = String(p.message || p.text || ev.event_type);
    const status = idleAfter.includes(ev.event_type) ? "idle" : "thinking";
    next = updateAgent(next, mapped, {
      status,
      currentSubtask: msg,
      lastMessage: String(p.text || p.message || ""),
    });
    if (status === "thinking" && msg) {
      next = appendAgentMonologue(next, mapped, msg);
    }
  }

  return next;
}

export function isManagerBusy(swarm: SwarmDashboardState): boolean {
  const manager = swarm.agents.MANAGER;
  return manager.status === "thinking" || manager.status === "recovering";
}

export function buildSwarmState(events: TelemetryEvent[]): SwarmDashboardState {
  return events.reduce(reduceSwarmEvent, initialSwarmState());
}

export function hudStatusColor(status: SwarmAgentStatus): string {
  switch (status) {
    case "thinking":
    case "recovering":
      return "bg-amber-400";
    case "alert":
      return "bg-red-500";
    default:
      return "bg-emerald-400";
  }
}

export function hudStatusAnimation(status: SwarmAgentStatus): string {
  switch (status) {
    case "thinking":
    case "recovering":
    case "alert":
      return "animate-pulse";
    default:
      return "";
  }
}

export function statusColor(status: SwarmAgentStatus): string {
  switch (status) {
    case "thinking":
    case "recovering":
      return "bg-amber-400";
    case "alert":
      return "bg-red-500";
    default:
      return "bg-emerald-500";
  }
}

export function statusAnimation(status: SwarmAgentStatus): string {
  switch (status) {
    case "thinking":
    case "recovering":
      return "animate-pulse";
    case "alert":
      return "animate-ping";
    default:
      return "";
  }
}
