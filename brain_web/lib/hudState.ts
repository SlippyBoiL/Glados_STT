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
};

export function deriveVoiceState(events: TelemetryEvent[]): HudVoiceState {
  if (!events.length) return "idle";

  const recent = events.slice(-16);
  for (let i = recent.length - 1; i >= 0; i--) {
    const ev = recent[i];
    const t = ev.event_type;
    if (t === "heard") return "listening";
    if (t === "llm_response") {
      const final = ev.payload?.final;
      if (final === true) return "speaking";
      return "thinking";
    }
    if (
      t === "thinking" ||
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
    if (t === "code_executed" || t === "monitor_alert" || t === "action_progress")
      return "acting";
  }
  return "idle";
}

export function buildThoughtTimeline(events: TelemetryEvent[]): ThoughtItem[] {
  const recent = events.slice(-80);
  const items: ThoughtItem[] = [];
  const lastTs = recent.length ? recent[recent.length - 1].ts : 0;

  for (const ev of recent) {
    const time = new Date(ev.ts * 1000).toLocaleTimeString();
    const p = ev.payload || {};

    if (ev.event_type === "thinking") {
      items.push({
        ts: ev.ts,
        time,
        phase: String(p.phase || "think"),
        message: String(p.message || ""),
        detail: String(p.detail || p.attempt || p.skill_id || "").slice(0, 120) || undefined,
        source: "thinking",
        active: ev.ts === lastTs,
      });
      continue;
    }

    if (ev.event_type === "heard") {
      items.push({
        ts: ev.ts,
        time,
        phase: "heard",
        message: `Heard: "${String(p.text || "").slice(0, 100)}"`,
        source: "event",
      });
    } else if (ev.event_type === "facility_brain") {
      items.push({
        ts: ev.ts,
        time,
        phase: "facility",
        message: "Facility brain handled request",
        detail: String(p.text || "").slice(0, 80),
        source: "event",
      });
    } else if (ev.event_type === "memory_retrieved") {
      items.push({
        ts: ev.ts,
        time,
        phase: "memory",
        message: "Memory + computer brain loaded",
        detail: String(p.context || "").slice(0, 80),
        source: "event",
      });
    } else if (ev.event_type === "skills_matched") {
      const skills = (p.skills as { id?: string; file?: string }[]) || [];
      items.push({
        ts: ev.ts,
        time,
        phase: "skills",
        message: p.conversational
          ? "Chat mode — no protocol run"
          : `Protocols matched: ${skills.length}`,
        detail: skills
          .map((s) => s.id || s.file)
          .filter(Boolean)
          .join(", ")
          .slice(0, 80),
        source: "event",
      });
    } else if (ev.event_type === "skill_learned") {
      items.push({
        ts: ev.ts,
        time,
        phase: "learn",
        message: p.success ? "Skill learned and saved" : "Skill learning failed",
        detail: String(p.message || "").slice(0, 80),
        source: "event",
      });
    } else if (ev.event_type === "llm_response" && !p.final) {
      items.push({
        ts: ev.ts,
        time,
        phase: "llm",
        message: "LLM reasoning…",
        detail: String(p.text || "").slice(0, 60),
        source: "event",
      });
    } else if (ev.event_type === "llm_response" && p.final) {
      items.push({
        ts: ev.ts,
        time,
        phase: "speak",
        message: "Speaking response",
        detail: String(p.text || "").slice(0, 60),
        source: "event",
      });
    } else if (ev.event_type === "code_executed") {
      items.push({
        ts: ev.ts,
        time,
        phase: "execute",
        message: p.success ? "Protocol executed" : "Execution failed",
        detail: String(p.output_preview || "").slice(0, 80),
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
    }
  }

  if (items.length) {
    items[items.length - 1].active = true;
  }
  return items.slice(-24);
}

export function lastSubtitle(events: TelemetryEvent[]): string {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i];
    if (ev.event_type === "thinking") {
      const text = String(ev.payload?.message || "").trim();
      if (text) return `Thinking: ${text.slice(0, 180)}`;
    }
    if (ev.event_type === "hud_chat" && ev.payload?.role === "thinking") {
      const text = String(ev.payload?.text || "").trim();
      if (text) return text.slice(0, 200);
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
  const time = new Date(ev.ts * 1000).toLocaleTimeString();
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
  else detail = JSON.stringify(p).slice(0, 50);
  return `[${time}] ${type} ${detail}`;
}
