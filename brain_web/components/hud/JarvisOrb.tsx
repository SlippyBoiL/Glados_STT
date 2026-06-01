"use client";

import { motion } from "framer-motion";
import type { HudVoiceState } from "@/lib/hudState";

const stateColors: Record<HudVoiceState, string> = {
  idle: "rgba(26, 140, 255, 0.4)",
  listening: "rgba(61, 214, 255, 0.7)",
  thinking: "rgba(193, 122, 58, 0.6)",
  speaking: "rgba(61, 214, 255, 0.9)",
  acting: "rgba(255, 80, 80, 0.65)",
};

type Props = {
  voiceState: HudVoiceState;
};

export function JarvisOrb({ voiceState }: Props) {
  const glow = stateColors[voiceState];
  const spin =
    voiceState === "thinking" ? 4 : voiceState === "acting" ? 2.5 : 12;

  return (
    <div className="relative flex h-[min(42vh,380px)] w-full items-center justify-center">
      {/* Outer rings */}
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border border-hud-cyan/20"
          style={{
            width: `${55 + i * 18}%`,
            height: `${55 + i * 18}%`,
          }}
          animate={{ rotate: i % 2 === 0 ? 360 : -360 }}
          transition={{
            duration: spin + i * 3,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      ))}

      {/* Tick ring */}
      <svg
        className="absolute h-[72%] w-[72%] opacity-40"
        viewBox="0 0 200 200"
      >
        {Array.from({ length: 48 }).map((_, i) => {
          const a = (i / 48) * Math.PI * 2;
          const x1 = 100 + Math.cos(a) * 88;
          const y1 = 100 + Math.sin(a) * 88;
          const x2 = 100 + Math.cos(a) * (i % 4 === 0 ? 96 : 92);
          const y2 = 100 + Math.sin(a) * (i % 4 === 0 ? 96 : 92);
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#3dd6ff"
              strokeWidth={i % 4 === 0 ? 1.5 : 0.5}
            />
          );
        })}
      </svg>

      {/* Core orb */}
      <motion.div
        className="relative z-10 rounded-full"
        style={{
          width: "28%",
          height: "28%",
          background: `radial-gradient(circle at 35% 35%, #7ee8ff, ${glow}, #030810 70%)`,
          boxShadow: `0 0 60px 20px ${glow}, inset 0 0 40px rgba(255,255,255,0.15)`,
        }}
        animate={{
          scale: voiceState === "listening" ? [1, 1.08, 1] : [1, 1.03, 1],
        }}
        transition={{
          duration: voiceState === "listening" ? 0.8 : 2,
          repeat: Infinity,
        }}
      />

      {/* State label */}
      <p className="absolute bottom-0 font-mono text-xs uppercase tracking-[0.35em] text-hud-cyan/70">
        {voiceState}
      </p>
    </div>
  );
}
