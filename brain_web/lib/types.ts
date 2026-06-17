export type TelemetryEvent = {
  ts: number;
  event_type: string;
  payload: Record<string, unknown>;
};

/** Swarm agent status for the multi-agent command dashboard. */
export type SwarmAgentStatus = "idle" | "thinking" | "alert" | "recovering";

export type SwarmAgentId =
  | "MANAGER"
  | "CORE_CODER"
  | "WEB_RESEARCHER"
  | "QA_FACT_CHECKER"
  | "DEVOPS_OVERSEER"
  | "FACILITY_MANAGER"
  | "MAINTENANCE_AGENT";

export type SwarmAgentState = {
  id: SwarmAgentId;
  name: string;
  status: SwarmAgentStatus;
  currentSubtask: string;
  lastMessage: string;
  lastActiveTs: number;
  pulseKey: number;
};

export type SwarmTelemetryPayload = {
  agent_id?: string;
  agent?: string;
  status?: SwarmAgentStatus | string;
  message?: string;
  current_subtask?: string;
  metrics?: { cpu?: number; ram?: number; disk?: number };
  timestamp?: string;
};

export type SystemMetricsPayload = {
  metrics?: { cpu?: number; ram?: number; disk?: number };
  timestamp?: string;
  detail?: Record<string, unknown>;
};

export type MaintenanceActionPayload = SwarmTelemetryPayload & {
  action?: string;
  detail?: Record<string, unknown>;
};

export type ServiceRegistryEntry = {
  id: string;
  name: string;
  ok: boolean;
  alerts: string[];
  lastTs: number;
};

export type SwarmDashboardState = {
  agents: Record<SwarmAgentId, SwarmAgentState>;
  monologue: string[];
  maintenanceLog: string[];
  metrics: { cpu: number; ram: number; disk: number };
  services: ServiceRegistryEntry[];
  lastPulseAgent: SwarmAgentId | null;
  pulseNonce: number;
  brainWriteNonce: number;
  lastBrainWriteTs: number;
  activeAgentId: SwarmAgentId | null;
  agentMonologue: string[];
};

export type BrainState = {
  last_heard?: { text?: string } | null;
  last_llm_response?: { text?: string; final?: boolean } | null;
  last_memory?: { query?: string; context?: string } | null;
  last_thinking?: { phase?: string; message?: string; detail?: string } | null;
  subsystem_status?: Record<string, unknown> | null;
  last_intent?: { category?: string; confidence?: number; routed?: boolean } | null;
  last_skills_matched?: {
    query?: string;
    skills?: { file: string; description: string }[];
  } | null;
  last_code_executed?: { output_preview?: string; success?: boolean } | null;
  last_monitor_alert?: { device?: string; alerts?: string[] } | null;
  subsystem_flags?: Record<string, unknown>;
  llm_config?: {
    provider?: string;
    model?: string;
    vision_model?: string;
    embedding_backend?: string;
  };
  skills_count?: number;
  computer_brain?: {
    fact_count?: number;
    synced_at_iso?: string | null;
    hostname?: string | null;
    file_index?: { file_count?: number };
  };
  event_count?: number;
};

export type Skill = {
  file: string;
  id?: string;
  description: string;
  category: string;
  status?: string;
  successes?: number;
  runs?: number;
};

export type GraphNode = {
  id: string;
  label: string;
  group: string;
  meta?: Record<string, unknown>;
};

export type GraphEdge = {
  source: string;
  target: string;
  type: string;
};

export type IntentCluster = {
  category: string;
  phrases: string[];
  count: number;
};

export type StaticFact = {
  id: string;
  keywords: string[];
  text: string;
  category?: string;
  baseline?: boolean;
};
