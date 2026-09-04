const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || ""
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888";

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("glados_brain_token") || ""
      : "";
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${path}: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant" | "thinking";
  text: string;
  ts?: number;
  source?: string;
  phase?: string;
  streaming?: boolean;
};

export function wsUrl(): string {
  const base = API_BASE || (typeof window !== "undefined" ? window.location.origin : "");
  const wsBase = base.replace(/^http/, "ws");
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("glados_brain_token") || ""
      : "";
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${wsBase}/ws/live${q}`;
}

export type SystemMetrics = {
  ts: number;
  hostname: string;
  platform: string;
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  network_sent_kbps: number;
  network_recv_kbps: number;
  error?: string;
};

export const api = {
  health: () => fetchJson<{ status: string }>("/api/health"),
  metrics: () => fetchJson<SystemMetrics>("/api/system/metrics"),
  state: () => fetchJson<import("./types").BrainState>("/api/brain/state"),
  recent: (limit = 200) =>
    fetchJson<{ events: import("./types").TelemetryEvent[] }>(
      `/api/telemetry/recent?limit=${limit}`,
    ),
  intents: () =>
    fetchJson<{ clusters: import("./types").IntentCluster[] }>("/api/brain/intents"),
  memories: () =>
    fetchJson<{
      static: import("./types").StaticFact[];
      chroma: { id: string; text: string; metadata: Record<string, unknown> }[];
      chroma_enabled: boolean;
      honcho_enabled?: boolean;
      honcho?: {
        enabled?: boolean;
        ready?: boolean;
        url?: string;
        workspace?: string;
        error?: string;
        user_card?: string;
        user_profile?: string;
        computer_profile?: string;
      };
      computer: import("./types").StaticFact[];
      computer_meta: {
        fact_count: number;
        synced_at_iso: string | null;
        hostname: string | null;
      };
    }>("/api/brain/memories"),
  computerBrain: () =>
    fetchJson<{
      facts: import("./types").StaticFact[];
      fact_count: number;
      synced_at_iso: string | null;
    }>("/api/brain/computer"),
  skills: () =>
    fetchJson<{ skills: import("./types").Skill[]; count: number }>(
      "/api/brain/skills",
    ),
  graph: () =>
    fetchJson<{
      nodes: import("./types").GraphNode[];
      edges: import("./types").GraphEdge[];
    }>("/api/brain/graph"),
  chatHistory: (limit = 150) =>
    fetchJson<{
      messages: ChatMessage[];
      count: number;
      session_started_at?: number | null;
      session?: { session_started_at?: number; boot_id?: string };
    }>(`/api/chat/history?limit=${limit}`),
  chatSend: (text: string) =>
    fetchJson<{ ok: boolean; id?: string; error?: string }>("/api/chat/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  /** Manual text override — bypasses STT, routes to Swarm Manager via inbox + telemetry. */
  sendUserPrompt: (text: string) =>
    fetchJson<{ ok: boolean; id?: string; error?: string }>("/api/chat/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
};
