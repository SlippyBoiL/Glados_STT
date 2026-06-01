export type TelemetryEvent = {
  ts: number;
  event_type: string;
  payload: Record<string, unknown>;
};

export type BrainState = {
  last_heard?: { text?: string } | null;
  last_llm_response?: { text?: string; final?: boolean } | null;
  last_memory?: { query?: string; context?: string } | null;
  subsystem_status?: Record<string, unknown> | null;
  last_intent?: { category?: string; confidence?: number; routed?: boolean } | null;
  last_skills_matched?: {
    query?: string;
    skills?: { file: string; description: string }[];
  } | null;
  last_code_executed?: { output_preview?: string; success?: boolean } | null;
  last_monitor_alert?: { device?: string; alerts?: string[] } | null;
  subsystem_flags?: Record<string, unknown>;
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
