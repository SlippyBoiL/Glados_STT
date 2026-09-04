"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
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

function telemetryToChat(events: TelemetryEvent[], cutoff: number): ChatMessage[] {
  const out: ChatMessage[] = [];
  let live: ChatMessage | null = null;
  let liveThink: ChatMessage | null = null;
  for (const ev of events) {
    if (cutoff > 0 && ev.ts < cutoff - 0.001) continue;
    const p = ev.payload || {};
    if (ev.event_type === "hud_chat") {
      const role = p.role as string | undefined;
      const text = String(p.text || "").trim();
      if (!text) continue;
      if (role === "thinking") {
        if (p.streaming === true) {
          liveThink = {
            id: "live-think",
            role: "thinking",
            text,
            ts: ev.ts,
            streaming: true,
          };
        } else {
          out.push({
            id: `think-done-${ev.ts}`,
            role: "thinking",
            text,
            ts: ev.ts,
            streaming: false,
          });
          liveThink = null;
        }
        continue;
      }
      if (role !== "user" && role !== "assistant") continue;
      // Skip pending flags that only mirror inbox enqueue
      if (p.pending === true && role === "user") continue;
      const msg: ChatMessage = {
        id: String(p.id || `${ev.ts}-${role}-${text.slice(0, 24)}`),
        role: role as "user" | "assistant",
        text,
        ts: ev.ts,
        streaming: p.streaming === true,
      };
      if (msg.id === "live-stream" || p.streaming === true) {
        live = { ...msg, id: "live-stream" };
        continue;
      }
      out.push(msg);
    } else if (ev.event_type === "heard") {
      // Avoid duplicating HUD text that also arrives as hud_chat / history
      continue;
    } else if (ev.event_type === "llm_response") {
      const text = String(p.text || "").trim();
      if (!text || text.startsWith("```")) continue;
      if (p.final === false) {
        live = {
          id: "live-stream",
          role: "assistant",
          text,
          ts: ev.ts,
          streaming: true,
        };
      }
      // final llm_response is also stored as hud_chat / history — skip to avoid dupes
    }
  }
  if (liveThink) out.push(liveThink);
  if (live) out.push(live);
  return out;
}

function mergeMessages(a: ChatMessage[], b: ChatMessage[]): ChatMessage[] {
  const byId = new Map<string, ChatMessage>();
  for (const m of [...a, ...b]) {
    const id = m.id || `${m.ts}-${m.role}-${m.text.slice(0, 32)}`;
    byId.set(id, { ...m, id });
  }
  const sorted = Array.from(byId.values()).sort(
    (x, y) => (x.ts || 0) - (y.ts || 0),
  );
  const out: ChatMessage[] = [];
  for (const m of sorted) {
    const prev = out[out.length - 1];
    const same =
      prev &&
      prev.role === m.role &&
      prev.text.trim() === m.text.trim() &&
      Math.abs((prev.ts || 0) - (m.ts || 0)) < 12;
    if (same) {
      // Prefer non-optimistic id
      if (String(prev.id || "").startsWith("pending-") && !String(m.id || "").startsWith("pending-")) {
        out[out.length - 1] = m;
      }
      continue;
    }
    out.push(m);
  }
  return out;
}

/** Right-rail live chat — sticky composer, latest messages, resilient API status. */
export function LiveChatPanel({
  events,
}: {
  events: TelemetryEvent[];
  /** @deprecated ignored — never lock the composer */
  disabled?: boolean;
}) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [cutoff, setCutoff] = useState(0);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const wsCutoff = useMemo(() => sessionCutoffFromEvents(events), [events]);
  const effectiveCutoff = Math.max(cutoff, wsCutoff);

  const live = useMemo(
    () => telemetryToChat(events, effectiveCutoff),
    [events, effectiveCutoff],
  );

  const messages = useMemo(() => {
    const merged = mergeMessages(history, live).filter(
      (m) => effectiveCutoff <= 0 || (m.ts || 0) >= effectiveCutoff - 0.001,
    );
    return merged.slice(-16);
  }, [history, live, effectiveCutoff]);

  const refresh = useCallback(() => {
    return api
      .chatHistory(80)
      .then((res) => {
        const c = Number(
          res.session_started_at ?? res.session?.session_started_at ?? 0,
        );
        if (c > 0) setCutoff(c);
        const msgs = res.messages || [];
        setHistory((prev) => {
          // Drop optimistic bubbles once real history contains the same text
          const texts = new Set(
            msgs.filter((m) => m.role === "user").map((m) => m.text.trim()),
          );
          const keptOptimistic = prev.filter(
            (m) =>
              String(m.id || "").startsWith("pending-") &&
              !texts.has(m.text.trim()),
          );
          return mergeMessages(msgs, keptOptimistic);
        });
        setApiOk(true);
      })
      .catch(() => {
        setApiOk((prev) => (prev === true ? prev : false));
      });
  }, []);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 2500);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
    bottomRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
  }, [messages]);

  // Clear sending lock if an assistant reply arrives
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last?.role === "assistant") setSending(false);
  }, [messages]);

  async function onSend(e?: React.FormEvent) {
    e?.preventDefault();
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
        setError(res.error || "Inbox busy — kernel still starting. Retry in a moment.");
        setDraft(text);
        setHistory((prev) => prev.filter((m) => m.id !== optimistic.id));
        return;
      }
      setApiOk(true);
      let tries = 0;
      const poll = setInterval(() => {
        tries += 1;
        void refresh();
        if (tries >= 12) clearInterval(poll);
      }, 1000);
    } catch {
      setApiOk(false);
      setError("Send failed — is tray_launcher / brain API on :8888?");
      setDraft(text);
      setHistory((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  }

  const statusLabel =
    apiOk === false ? "API OFFLINE" : apiOk === true ? "LINKED" : "CONNECTING…";
  const statusClass =
    apiOk === false
      ? "text-red-400"
      : apiOk === true
        ? "text-emerald-400"
        : "text-[#00F0FF]/40";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <motion.div
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        className="jarvis-glass flex min-h-0 flex-1 flex-col overflow-hidden"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-[#00F0FF]/15 px-4 py-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[#00F0FF]/80">
              Live Chat
            </p>
            <p className="mt-0.5 font-mono text-[9px] text-[#00F0FF]/35">
              Talk to GLaDOS · replies stream here
            </p>
          </div>
          <span className={`font-mono text-[9px] ${statusClass}`}>{statusLabel}</span>
        </div>

        <div
          ref={listRef}
          className="min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-3"
        >
          {messages.length === 0 ? (
            <p className="font-mono text-[11px] text-[#00F0FF]/35">
              Type below to open a channel. Example: &quot;Are you online?&quot;
            </p>
          ) : (
            messages.map((m) => {
              const isUser = m.role === "user";
              const isThink = m.role === "thinking";
              return (
                <div
                  key={m.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[92%] rounded-sm border px-3 py-2 font-mono text-[12px] leading-relaxed ${
                      isUser
                        ? "border-emerald-400/30 bg-emerald-950/40 text-emerald-100"
                        : isThink
                          ? "border-violet-400/30 bg-violet-950/40 text-violet-100 italic"
                          : "border-[#00F0FF]/25 bg-[#001820]/80 text-[#B8F4FF]"
                    }`}
                  >
                    <p className="mb-1 text-[8px] uppercase tracking-[0.2em] opacity-50">
                      {isUser ? "Operator" : isThink ? "GLaDOS thoughts" : "GLaDOS"}
                      {m.streaming ? " · streaming" : ""}
                    </p>
                    <p className="whitespace-pre-wrap break-words">{m.text}</p>
                  </div>
                </div>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={onSend}
          className="shrink-0 border-t border-[#00F0FF]/15 bg-[#00050b]/80 p-3 backdrop-blur-md"
        >
          <div className="flex gap-2">
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={sending}
              placeholder="Message GLaDOS…"
              aria-label="Live chat message"
              className="min-w-0 flex-1 rounded-sm border border-[#00F0FF]/25 bg-black/60 px-3 py-3 font-mono text-sm text-[#00F0FF] placeholder:text-[#00F0FF]/30 outline-none focus:border-[#00F0FF]/60 focus:ring-1 focus:ring-[#00F0FF]/40 disabled:opacity-50"
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={sending || !draft.trim()}
              className="shrink-0 rounded-sm border border-[#00F0FF]/40 bg-[#00F0FF]/10 px-4 py-3 font-mono text-[11px] uppercase tracking-[0.15em] text-[#00F0FF] transition hover:bg-[#00F0FF]/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {sending ? "…" : "Send"}
            </button>
          </div>
          {error ? (
            <p className="mt-1.5 font-mono text-[10px] text-red-400">{error}</p>
          ) : (
            <p className="mt-1.5 font-mono text-[9px] text-[#00F0FF]/30">
              Enter to send · phone SMS: text your Google Voice number, or publish on ntfy
            </p>
          )}
        </form>
      </motion.div>
    </div>
  );
}
