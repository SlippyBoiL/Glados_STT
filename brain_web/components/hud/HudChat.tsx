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
  for (const ev of events) {
    if (sessionCutoff > 0 && ev.ts < sessionCutoff - 0.001) continue;
    const p = ev.payload || {};
    if (ev.event_type === "hud_chat") {
      const role = p.role as string | undefined;
      const text = String(p.text || "").trim();
      if (!text) continue;
      if (role === "thinking") continue;
      if (role !== "user" && role !== "assistant") continue;
      out.push({
        id: String(p.id || `${ev.ts}-${role}-${text.slice(0, 24)}`),
        role: role as "user" | "assistant",
        text,
        ts: ev.ts,
        source: p.source as string | undefined,
      });
    } else if (ev.event_type === "thinking") {
      const text = String(p.message || "").trim();
      if (text) {
        out.push({
          id: `think-${ev.ts}-${text.slice(0, 16)}`,
          role: "thinking",
          text: `[${p.phase || "think"}] ${text}`,
          ts: ev.ts,
          phase: String(p.phase || ""),
        });
      }
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
    } else if (ev.event_type === "llm_response" && p.final !== false) {
      const text = String(p.text || "").trim();
      if (text && !text.startsWith("```")) {
        out.push({
          id: `llm-${ev.ts}`,
          role: "assistant",
          text,
          ts: ev.ts,
        });
      }
    }
  }
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
  return Array.from(byId.values()).sort(
    (a, b) => (a.ts || 0) - (b.ts || 0),
  );
}

export function HudChat({ events }: { events: TelemetryEvent[] }) {
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
    const t = setInterval(refreshHistory, 2500);
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
      await api.chatSend(text);
      // Do not await history refresh — a slow/hung poll left sending=true and blocked the second HUD message.
      void refreshHistory().catch(() => {});
    } catch {
      setError("Send failed — is the brain API running on port 8080?");
      setDraft(text);
      setHistory((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="hud-panel flex h-[min(42vh,440px)] min-h-[300px] flex-col p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-hud-cyan">
          Text channel
        </p>
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
            Type below — your messages, GLaDOS replies, and her thinking stream
            appear here.
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
                      ? "Thinking"
                      : "GLaDOS"}
                </p>
                <p className="mt-0.5 whitespace-pre-wrap break-words">{m.text}</p>
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
          placeholder="Message Glados…"
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
