"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { TelemetryEvent } from "@/lib/types";

type Stage = {
  key: string;
  label: string;
  className: string;
  content: string;
  ts?: number;
};

function buildStages(events: TelemetryEvent[]): Stage[] {
  const recent = events.slice(-30);
  const byType: Record<string, TelemetryEvent | undefined> = {};
  for (const ev of [...recent].reverse()) {
    if (!byType[ev.event_type]) byType[ev.event_type] = ev;
  }

  const stages: Stage[] = [];

  const heard = byType.heard;
  if (heard) {
    stages.push({
      key: "heard",
      label: "Heard",
      className: "stage-hearing",
      content: String(heard.payload?.text || ""),
      ts: heard.ts,
    });
  }

  const intent = byType.intent_classified;
  if (intent) {
    stages.push({
      key: "intent",
      label: "Intent",
      className: "stage-intent",
      content: `${intent.payload?.category || "?"} — ${Number(intent.payload?.confidence || 0).toFixed(1)}%`,
      ts: intent.ts,
    });
  }

  const memory = byType.memory_retrieved;
  if (memory) {
    const ctx = String(memory.payload?.context || "");
    const lines = ctx.split("\n").filter(Boolean).length;
    stages.push({
      key: "memory",
      label: "Memory",
      className: "stage-memory",
      content: lines ? `${lines} context line(s) retrieved` : "No memory hit",
      ts: memory.ts,
    });
  }

  const skills = byType.skills_matched;
  if (skills) {
    const list = (skills.payload?.skills as { file: string }[]) || [];
    stages.push({
      key: "skills",
      label: "Skills",
      className: "stage-intent",
      content: list.length
        ? list.map((s) => s.file).join(", ")
        : "No protocol match",
      ts: skills.ts,
    });
  }

  const llm = byType.llm_response;
  if (llm) {
    const text = String(llm.payload?.text || "").slice(0, 280);
    stages.push({
      key: "llm",
      label: "LLM",
      className: "stage-reason",
      content: text + (String(llm.payload?.text || "").length > 280 ? "…" : ""),
      ts: llm.ts,
    });
  }

  const exec = byType.code_executed;
  if (exec) {
    stages.push({
      key: "exec",
      label: "Execute",
      className: "stage-action",
      content: String(exec.payload?.output_preview || "").slice(0, 200),
      ts: exec.ts,
    });
  }

  return stages;
}

type Props = {
  events: TelemetryEvent[];
};

export function ThoughtPipeline({ events }: Props) {
  const stages = buildStages(events);

  return (
    <div className="panel p-4">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-aperture-muted">
        Thought Pipeline
      </h2>
      {stages.length === 0 ? (
        <p className="text-sm text-aperture-muted">
          Waiting for Glados to think…
        </p>
      ) : (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {stages.map((s, i) => (
              <motion.div
                key={s.key}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                className={`rounded border-l-4 bg-black/20 px-3 py-2 ${s.className}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase text-aperture-orange">
                    {i + 1}. {s.label}
                  </span>
                  {s.ts ? (
                    <span className="font-mono text-[10px] text-aperture-muted">
                      {new Date(s.ts * 1000).toLocaleTimeString()}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                  {s.content}
                </p>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
