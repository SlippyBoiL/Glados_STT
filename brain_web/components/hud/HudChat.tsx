"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type ChatMessage } from "@/lib/api";
import type { TelemetryEvent } from "@/lib/types";

function sessionCutoffFromEvents(events: TelemetryEvent[]): number {
  let cutoff = 0;
  for (const ev of events) {
    if (ev.event_type !== "chat_session_reset") continue;
    const ts = Number(ev.payload?.session_started_at ?? ev.ts);
    if (ts > cutoff) cutoff = ts;
  }
  return cutoff;
}

function filterBySession(messages: ChatMessage[], cutoff: number): ChatMessage[] {
  if (cutoff <= 0) return messages;
  return messages.filter((m) => (m.ts || 0) >= cutoff - 0.001);
}

function telemetryToMessages(events: TelemetryEvent[], sessionCutoff = 0): ChatMessage[] {
  const out: ChatMessage[] = [];
  let liveStreamMsg: ChatMessage | null = null;
  let liveThinkMsg: ChatMessage | null = null;
  for (const ev of events) {
    if (sessionCutoff > 0 && ev.ts < sessionCutoff - 0.001) continue;
    const p = ev.payload || {};
    if (ev.event_type === "hud_chat") {
      const role = p.role as string | undefined;
      const text = String(p.text || "").trim();
      if (!text) continue;
      const msg: ChatMessage = {
        id: String(p.id || `${ev.ts}-${role}-${text.slice(0, 24)}`),
        role: (role as ChatMessage["role"]) || "assistant",
        text,
        ts: ev.ts,
        source: p.source as string | undefined,
        streaming: p.streaming === true,
      };
      if (role === "thinking") {
        if (msg.id === "live-think" || p.streaming === true) {
          if (p.streaming === true) {
            liveThinkMsg = { ...msg, id: "live-think" };
          } else {
            out.push({
              ...msg,
              id: `think-done-${ev.ts}`,
              streaming: false,
            });
            liveThinkMsg = null;
          }
          continue;
        }
        out.push(msg);
        continue;
      }
      if (role !== "user" && role !== "assistant") continue;
      if (msg.id === "live-stream" || p.streaming === true) {
        liveStreamMsg = { ...msg, id: "live-stream" };
        continue;
      }
      out.push(msg);
    } else if (ev.event_type === "thinking") {
      const text = String(p.message || "").trim();
      const phase = String(p.phase || "");
      if (!text) continue;
      if (phase === "done") continue;
      if (phase === "llm" && /^thinking/i.test(text)) continue;
      out.push({
        id: `think-${ev.ts}-${text.slice(0, 16)}`,
        role: "thinking",
        text: `[${phase || "think"}] ${text}`,
        ts: ev.ts,
        phase,
      });
    } else if (ev.event_type === "action_progress") {
      const text = String(p.message || "").trim();
      if (text) {
        out.push({
          id: `action-${ev.ts}-${text.slice(0, 16)}`,
          role: "thinking",
          text: `⚙ ${text}`,
          ts: ev.ts,
          phase: String(p.phase || "action"),
        });
      }
    } else if (ev.event_type === "heard") {
      const text = String(p.text || "").trim();
      if (text) {
        out.push({
          id: `heard-${ev.ts}`,
          role: "user",
          text,
          ts: ev.ts,
          source: "voice",
        });
      }
    } else if (ev.event_type === "llm_response") {
      const text = String(p.text || "").trim();
      if (!text || text.startsWith("```")) continue;
      if (p.final === false) {
        liveStreamMsg = {
          id: "live-stream",
          role: "assistant",
          text,
          ts: ev.ts,
          streaming: true,
        };
      } else if (!liveStreamMsg || liveStreamMsg.streaming) {
        liveStreamMsg = {
          id: "live-stream",
          role: "assistant",
          text,
          ts: ev.ts,
          streaming: false,
        };
      }
    }
  }
  if (liveThinkMsg) out.push(liveThinkMsg);
  if (liveStreamMsg) out.push(liveStreamMsg);
  return out;
}

function mergeMessages(
  history: ChatMessage[],
  live: ChatMessage[],
): ChatMessage[] {
  const byId = new Map<string, ChatMessage>();
  const add = (m: ChatMessage) => {
    const id =
      m.id ||
      `${m.ts || 0}-${m.role}-${m.text.slice(0, 32)}`;
    byId.set(id, { ...m, id });
  };
  for (const m of history) add(m);
  for (const m of live) add(m);
  // Drop near-duplicate assistant lines (same text within 8s) — history+telemetry overlap
  const sorted = Array.from(byId.values()).sort(
    (a, b) => (a.ts || 0) - (b.ts || 0),
  );
  const out: ChatMessage[] = [];
  for (const m of sorted) {
    const prev = out[out.length - 1];
    if (
      prev &&
      prev.role === m.role &&
      prev.role === "assistant" &&
      prev.text.trim() === m.text.trim() &&
      Math.abs((prev.ts || 0) - (m.ts || 0)) < 8
    ) {
      continue;
    }
    out.push(m);
  }
  return out;
}

export function HudChat({
  events,
  title = "Command GLaDOS",
  subtitle = "Type a message — thoughts stream silently; GLaDOS speaks the reply.",
  className = "",
}: {
  events: TelemetryEvent[];
  title?: string;
  subtitle?: string;
  className?: string;
}) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [sessionCutoff, setSessionCutoff] = useState(0);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const wsSessionCutoff = useMemo(
    () => sessionCutoffFromEvents(events),
    [events],
  );
  const effectiveCutoff = Math.max(sessionCutoff, wsSessionCutoff);

  const liveFromWs = useMemo(
    () => telemetryToMessages(events, effectiveCutoff),
    [events, effectiveCutoff],
  );
  const messages = useMemo(
    () => filterBySession(mergeMessages(history, liveFromWs), effectiveCutoff),
    [history, liveFromWs, effectiveCutoff],
  );

  const refreshHistory = useCallback(() => {
    return api
      .chatHistory(200)
      .then((res) => {
        const cutoff = Number(
          res.session_started_at ?? res.session?.session_started_at ?? 0,
        );
        if (cutoff > 0) setSessionCutoff(cutoff);
        const msgs = res.messages || [];
        setHistory(cutoff > 0 ? filterBySession(msgs, cutoff) : msgs);
      })
      .then(() => api.recent(120))
      .then((res) => {
        const cutoff = Math.max(
          sessionCutoff,
          sessionCutoffFromEvents(res.events || []),
        );
        if (cutoff > 0) setSessionCutoff(cutoff);
        const fromTel = telemetryToMessages(res.events || [], cutoff);
        setHistory((prev) =>
          filterBySession(mergeMessages(prev, fromTel), cutoff),
        );
        setApiOk(true);
        setError(null);
      })
      .catch((e) => {
        setApiOk(false);
        setError(
          e instanceof Error
            ? `Chat API offline: ${e.message}`
            : "Chat API offline — start brain_server / tray_launcher",
        );
      });
  }, [sessionCutoff]);

  useEffect(() => {
    refreshHistory();
    const t = setInterval(refreshHistory, 5000);
    return () => clearInterval(t);
  }, [refreshHistory]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);
    setDraft("");
    const optimistic: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      text,
      ts: Date.now() / 1000,
      source: "hud",
    };
    setHistory((prev) => [...prev, optimistic]);
    try {
      const res = await api.chatSend(text);
      if (!res.ok) {
        setError(res.error || "Kernel inbox busy — wait a moment and retry");
        setDraft(text);
        setHistory((prev) => prev.filter((m) => m.id !== optimistic.id));
        return;
      }
      void refreshHistory().catch(() => {});
    } catch {
      setError("Send failed — is the brain API running on port 8888?");
      setDraft(text);
      setHistory((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className={`hud-panel flex h-[min(42vh,440px)] min-h-[300px] flex-col p-3 ${className}`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
            {title}
          </p>
          <p className="mt-0.5 font-mono text-[9px] text-hud-cyan/45">{subtitle}</p>
        </div>
        <span
          className={`font-mono text-[9px] ${
            apiOk === false ? "text-red-400" : "text-hud-cyan/40"
          }`}
        >
          {apiOk === false
            ? "API offline"
            : `${messages.length} message${messages.length === 1 ? "" : "s"}`}
        </span>
      </div>
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 font-mono text-xs"
      >
        {messages.length === 0 ? (
          <p className="text-hud-cyan/40">
            Example: &quot;Research the latest Python release notes&quot; or
            &quot;Open github.com and summarize the README&quot;
          </p>
        ) : (
          messages.map((m) => (
            <div
              key={m.id || `${m.ts}-${m.role}`}
              className={`flex ${
                m.role === "user"
                  ? "justify-end"
                  : m.role === "thinking"
                    ? "justify-center"
                    : "justify-start"
              }`}
            >
              <div
                className={`max-w-[92%] rounded px-2 py-1.5 leading-relaxed ${
                  m.role === "user"
                    ? "border border-hud-cyan/25 bg-hud-cyan/10 text-hud-cyan"
                    : m.role === "thinking"
                      ? "border border-violet-500/25 bg-violet-500/10 text-violet-200/90 italic"
                      : "border border-orange-500/30 bg-orange-500/10 text-orange-100"
                }`}
              >
                <p className="text-[9px] uppercase tracking-wider opacity-50">
                  {m.role === "user"
                    ? m.source === "hud"
                      ? "You (HUD)"
                      : m.source === "voice"
                        ? "You (voice)"
                        : "You"
                    : m.role === "thinking"
                      ? "GLaDOS thoughts"
                      : "GLaDOS"}
                </p>
                <p className="mt-0.5 whitespace-pre-wrap break-words">
                  {m.text}
                  {m.streaming ? (
                    <span
                      className={`ml-0.5 inline-block h-3 w-1.5 animate-pulse align-middle ${
                        m.role === "thinking" ? "bg-violet-300/90" : "bg-orange-300/90"
                      }`}
                    />
                  ) : null}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
      {error ? (
        <p className="mt-1 shrink-0 text-[10px] text-red-400">{error}</p>
      ) : null}
      <form onSubmit={onSend} className="mt-2 flex shrink-0 gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Command GLaDOS — git push, diagnose, research…"
          disabled={sending}
          className="flex-1 rounded border border-hud-cyan/20 bg-black/40 px-3 py-2 font-mono text-xs text-hud-cyan placeholder:text-hud-cyan/30 focus:border-hud-cyan/50 focus:outline-none"
          maxLength={4000}
        />
        <button
          type="submit"
          disabled={sending || !draft.trim()}
          className="rounded border border-hud-cyan/30 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-hud-cyan hover:bg-hud-cyan/10 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
