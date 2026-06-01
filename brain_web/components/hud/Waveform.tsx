"use client";

import { useEffect, useState } from "react";
import type { HudVoiceState } from "@/lib/hudState";

type Props = {
  voiceState: HudVoiceState;
};

export function Waveform({ voiceState }: Props) {
  const [bars, setBars] = useState<number[]>(() =>
    Array.from({ length: 32 }, () => 0.2),
  );

  useEffect(() => {
    const active =
      voiceState === "listening" ||
      voiceState === "speaking" ||
      voiceState === "thinking";
    if (!active) {
      setBars(Array.from({ length: 32 }, () => 0.15));
      return;
    }
    const id = setInterval(() => {
      setBars(
        Array.from({ length: 32 }, () => {
          const base =
            voiceState === "speaking"
              ? 0.5
              : voiceState === "listening"
                ? 0.35
                : 0.25;
          return base + Math.random() * (voiceState === "speaking" ? 0.5 : 0.4);
        }),
      );
    }, 80);
    return () => clearInterval(id);
  }, [voiceState]);

  return (
    <div className="flex h-16 items-end justify-center gap-[3px] px-2">
      {bars.map((h, i) => (
        <div
          key={i}
          className="w-1 rounded-sm bg-gradient-to-t from-hud-glow to-hud-cyan"
          style={{
            height: `${h * 100}%`,
            opacity: 0.5 + h * 0.5,
            boxShadow: "0 0 6px rgba(61, 214, 255, 0.4)",
          }}
        />
      ))}
    </div>
  );
}
