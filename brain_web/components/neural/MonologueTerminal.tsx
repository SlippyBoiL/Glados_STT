"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { TerminalMonologueLine } from "@/lib/neuralState";
import { CommandOverrideBar } from "@/components/hud/CommandOverrideBar";

const TONE: Record<TerminalMonologueLine["tone"], string> = {
  cyan: "text-[#00F0FF]",
  amber: "text-amber-400",
  violet: "text-violet-300",
  dim: "text-[#00F0FF]/40",
  green: "text-emerald-400",
};

export function MonologueTerminal({
  lines,
  connected,
  disabled,
}: {
  lines: TerminalMonologueLine[];
  connected: boolean;
  disabled?: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="jarvis-glass flex min-h-0 flex-1 flex-col overflow-hidden"
      >
        <div className="border-b border-[#00F0FF]/15 px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[#00F0FF]/80">
            Internal Monologue
          </p>
          <p className="mt-0.5 font-mono text-[9px] text-[#00F0FF]/35">
            Live cognitive stream · capability tags · vocalization
          </p>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3 font-mono text-[11px] leading-relaxed">
          <AnimatePresence initial={false}>
            {lines.length === 0 && (
              <p className="text-[#00F0FF]/30">
                Awaiting neural activity…
              </p>
            )}
            {lines.map((line) => (
              <motion.div
                key={line.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-1.5 border-l border-[#00F0FF]/15 pl-2"
              >
                <span className={`${TONE[line.tone]} opacity-70`}>
                  [{line.tag}]
                </span>{" "}
                <span className="text-[#B8F4FF]/85">{line.text}</span>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>
      </motion.div>

      <div className="jarvis-glass shrink-0 p-3">
        <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-[#00F0FF]/50">
          Operator directive
        </p>
        <CommandOverrideBar disabled={!!disabled} connected={connected} />
      </div>
    </div>
  );
}
