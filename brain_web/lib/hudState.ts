import type { TelemetryEvent } from "./types";

export type HudVoiceState = "idle" | "listening" | "thinking" | "speaking" | "acting";

export type ThoughtItem = {
  ts: number;
  time: string;
  phase: string;
  message: string;
  detail?: string;
  active?: boolean;
  source: "thinking" | "event";
  turnStart?: boolean;
};

export type ThoughtTurn = {
  id: string;
  label: string;
  items: ThoughtItem[];
};

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString();
}

function detailFromPayload(p: Record<string, unknown>): string | undefined {
  const parts: string[] = [];
  for (const key of ["detail", "text", "message", "context", "output_preview", "skill_id", "attempt"]) {
    const val = p[key];
    if (val != null && String(val).trim()) {
      parts.push(String(val).trim());
    }
  }
  if (!parts.length) return undefined;
  return parts.join(" · ").slice(0, 280);
}

export function buildThoughtTimeline(events: TelemetryEvent[]): ThoughtItem[] {
  const recent = events.slice(-120);
  const items: ThoughtItem[] = [];
  let lastHeardTs = 0;

  for (const ev of recent) {
    const time = formatTime(ev.ts);
    const p = ev.payload || {};

    if (ev.event_type === "heard") {
      lastHeardTs = ev.ts;
      items.push({
        ts: ev.ts,
        time,
        phase: "heard",
        message: `Heard: "${String(p.text || "").slice(0, 120)}"`,
        source: "event",
        turnStart: true,
      });
      continue;
    }

    if (ev.event_type === "hud_chat" && p.role === "user") {
      items.push({
        ts: ev.ts,
        time,
        phase: "heard",
        message: `HUD: "${String(p.text || "").slice(0, 120)}"`,
        source: "event",
        turnStart: true,
      });
      continue;
    }

    // Skip hud_chat thinking duplicates — kernel emits structured `thinking` events.
    if (ev.event_type === "hud_chat" && p.role === "thinking") {
      continue;
    }

    if (ev.event_type === "thinking") {
      items.push({
        ts: ev.ts,
        time,
        phase: String(p.phase || "think"),
        message: String(p.message || ""),
        detail: detailFromPayload(p),
        source: "thinking",
      });
      continue;
    }

    if (ev.event_type === "facility_brain") {
      items.push({
        ts: ev.ts,
        time,
        phase: "facility",
        message: "Facility brain handled request",
        detail: detailFromPayload(p),
        source: "event",
      });
    } else if (ev.event_type === "facility_scan") {
      items.push({
        ts: ev.ts,
        time,
        phase: "facility",
        message: "Facility scan completed",
        detail: `Programs: ${p.programs ?? "?"}, files indexed: ${p.files_indexed ?? "?"}`,
        source: "event",
      });
    } else if (ev.event_type === "intent_classified") {
      items.push({
        ts: ev.ts,
        time,
        phase: "intent",
        message: `Intent: ${String(p.category || "?")} (${Number(p.confidence || 0).toFixed(0)}%)`,
        detail: p.routed ? "Routed to skill path" : "Conversation path",
        source: "event",
      });
    } else if (ev.event_type === "memory_retrieved") {
      const ctx = String(p.context || "");
      const lines = ctx.split("\n").filter(Boolean).length;
      items.push({
        ts: ev.ts,
        time,
        phase: "memory",
        message: lines ? `Memory loaded (${lines} lines)` : "Memory context empty",
        detail: ctx.slice(0, 280) || undefined,
        source: "event",
      });
    } else if (ev.event_type === "memory_consolidated") {
      items.push({
        ts: ev.ts,
        time,
        phase: "memory",
        message: "New fact consolidated",
        detail: String(p.fact || "").slice(0, 200),
        source: "event",
      });
    } else if (ev.event_type === "skills_matched") {
      const skills = (p.skills as { id?: string; file?: string }[]) || [];
      items.push({
        ts: ev.ts,
        time,
        phase: "skills",
        message: p.conversational
          ? "Chat mode — protocols not executed"
          : skills.length
            ? `Matched ${skills.length} protocol(s)`
            : "No protocol match",
        detail: skills
          .map((s) => s.id || s.file)
          .filter(Boolean)
          .join(", ")
          .slice(0, 120),
        source: "event",
      });
    } else if (ev.event_type === "skill_learned") {
      items.push({
        ts: ev.ts,
        time,
        phase: "learn",
        message: p.success ? "Skill learned and saved" : "Skill learning failed",
        detail: detailFromPayload(p),
        source: "event",
      });
    } else if (ev.event_type === "llm_response" && !p.final) {
      items.push({
        ts: ev.ts,
        time,
        phase: "llm",
        message: "LLM reasoning…",
        detail: String(p.text || "").slice(0, 120),
        source: "event",
      });
    } else if (ev.event_type === "llm_response" && p.final) {
      items.push({
        ts: ev.ts,
        time,
        phase: "speak",
        message: "Speaking response",
        detail: String(p.text || "").slice(0, 120),
        source: "event",
      });
    } else if (ev.event_type === "code_executed") {
      items.push({
        ts: ev.ts,
        time,
        phase: "execute",
        message: p.success ? "Protocol executed" : "Execution failed",
        detail: detailFromPayload(p),
        source: "event",
      });
    } else if (ev.event_type === "os_action") {
      items.push({
        ts: ev.ts,
        time,
        phase: "execute",
        message: "OS action completed",
        detail: detailFromPayload(p),
        source: "event",
      });
    } else if (ev.event_type === "action_progress") {
      items.push({
        ts: ev.ts,
        time,
        phase: String(p.phase || "action"),
        message: String(p.message || "Working…"),
        source: "event",
      });
    } else if (ev.event_type === "browser_step") {
      items.push({
        ts: ev.ts,
        time,
        phase: "browser",
        message: String(p.message || "Browser step"),
        detail: String(p.reason || "").slice(0, 120) || undefined,
        source: "event",
      });
    } else if (ev.event_type === "cursor_prompt") {
      items.push({
        ts: ev.ts,
        time,
        phase: "research",
        message: "Cursor prompt injected",
        detail: String(p.markdown || "").slice(0, 120),
        source: "event",
      });
    } else if (ev.event_type === "monitor_alert") {
      items.push({
        ts: ev.ts,
        time,
        phase: "monitor",
        message: `Alert: ${String(p.device || "subsystem")}`,
        detail: ((p.alerts as string[]) || []).join("; ").slice(0, 120),
        source: "event",
      });
    }

    void lastHeardTs;
  }

  if (items.length) {
    items[items.length - 1].active = true;
  }
  return items.slice(-48);
}

export function groupThoughtTimeline(items: ThoughtItem[]): ThoughtTurn[] {
  const turns: ThoughtTurn[] = [];
  let current: ThoughtItem[] = [];
  let turnIndex = 0;

  const flush = () => {
    if (!current.length) return;
    turns.push({
      id: `turn-${turnIndex}`,
      label: current[0]?.message?.slice(0, 60) || `Turn ${turnIndex + 1}`,
      items: current,
    });
    current = [];
    turnIndex += 1;
  };

  for (const item of items) {
    if (item.turnStart && current.length) {
      flush();
    }
    current.push(item);
  }
  flush();
  return turns.slice(-6);
}

export function currentThoughtPhase(events: TelemetryEvent[]): string {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i];
    if (ev.event_type === "thinking") {
      return String(ev.payload?.phase || "thinking");
    }
    if (ev.event_type === "action_progress") {
      return String(ev.payload?.phase || "acting");
    }
    if (ev.event_type === "heard" || (ev.event_type === "hud_chat" && ev.payload?.role === "user")) {
      return "heard";
    }
  }
  return "idle";
}

export function deriveVoiceState(events: TelemetryEvent[]): HudVoiceState {
  if (!events.length) return "idle";

  const recent = events.slice(-20);
  for (let i = recent.length - 1; i >= 0; i--) {
    const ev = recent[i];
    const t = ev.event_type;
    if (t === "heard" || (t === "hud_chat" && ev.payload?.role === "user")) return "listening";
    if (t === "llm_response") {
      const final = ev.payload?.final;
      if (final === true) return "speaking";
      return "thinking";
    }
    if (
      t === "thinking" ||
      t === "browser_step" ||
      t === "memory_retrieved" ||
      t === "intent_classified" ||
      t === "skills_matched" ||
      t === "skill_learned" ||
      t === "facility_brain" ||
      t === "facility_scan" ||
      t === "cursor_prompt"
    ) {
      return "thinking";
    }
    if (t === "code_executed" || t === "monitor_alert" || t === "action_progress" || t === "os_action")
      return "acting";
  }
  return "idle";
}

export function lastSubtitle(events: TelemetryEvent[]): string {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i];
    if (ev.event_type === "thinking") {
      const text = String(ev.payload?.message || "").trim();
      if (text) return `Thinking: ${text.slice(0, 180)}`;
    }
    if (ev.event_type === "hud_chat" && ev.payload?.role === "assistant") {
      const text = String(ev.payload?.text || "").trim();
      if (text) return text.slice(0, 200);
    }
    if (ev.event_type === "llm_response") {
      const text = String(ev.payload?.text || "").trim();
      if (text && !text.startsWith("```")) {
        return text.slice(0, 200);
      }
    }
    if (ev.event_type === "heard") {
      const heard = String(ev.payload?.text || "").trim();
      const low = heard.toLowerCase();
      if (low === "exit" || low === "quit" || low === "shutdown") {
        continue;
      }
      return `Subject: "${heard.slice(0, 120)}"`;
    }
  }
  return "Facility systems nominal. Awaiting test subject.";
}

export function formatTelemetryLine(ev: TelemetryEvent): string {
  const time = formatTime(ev.ts);
  const type = ev.event_type.toUpperCase().padEnd(18);
  let detail = "";
  const p = ev.payload || {};
  if (ev.event_type === "heard") detail = String(p.text || "").slice(0, 60);
  else if (ev.event_type === "hud_chat")
    detail = `${p.role}: ${String(p.text || "").slice(0, 50)}`;
  else if (ev.event_type === "llm_response")
    detail = String(p.text || "").slice(0, 50).replace(/\n/g, " ");
  else if (ev.event_type === "intent_classified")
    detail = `${p.category} ${p.confidence}%`;
  else if (ev.event_type === "monitor_alert")
    detail = `${p.device}: ${(p.alerts as string[])?.[0] || "alert"}`;
  else if (ev.event_type === "thinking")
    detail = `[${p.phase}] ${String(p.message || "").slice(0, 40)}`;
  else if (ev.event_type === "skill_learned")
    detail = p.success ? "ok" : "fail";
  else if (ev.event_type === "facility_brain")
    detail = String(p.text || "").slice(0, 40);
  else if (ev.event_type === "action_progress")
    detail = String(p.message || "").slice(0, 50);
  else detail = JSON.stringify(p).slice(0, 50);
  return `[${time}] ${type} ${detail}`;
}
