"use client";

import { motion } from "framer-motion";

export function Radar() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[180px]">
      <svg viewBox="0 0 120 120" className="h-full w-full">
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke="rgba(61, 214, 255, 0.15)"
          strokeWidth="1"
        />
        <circle
          cx="60"
          cy="60"
          r="36"
          fill="none"
          stroke="rgba(61, 214, 255, 0.1)"
          strokeWidth="1"
        />
        <circle
          cx="60"
          cy="60"
          r="18"
          fill="none"
          stroke="rgba(61, 214, 255, 0.1)"
          strokeWidth="1"
        />
        {[0, 45, 90, 135].map((deg) => (
          <line
            key={deg}
            x1="60"
            y1="60"
            x2={60 + 54 * Math.cos((deg * Math.PI) / 180)}
            y2={60 + 54 * Math.sin((deg * Math.PI) / 180)}
            stroke="rgba(61, 214, 255, 0.12)"
          />
        ))}
        <motion.line
          x1="60"
          y1="60"
          x2="60"
          y2="8"
          stroke="rgba(61, 214, 255, 0.7)"
          strokeWidth="2"
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "60px 60px" }}
        />
        <circle cx="60" cy="60" r="3" fill="#3dd6ff" />
        {/* blips */}
        <circle cx="78" cy="42" r="2" fill="#3dd6ff" opacity="0.8" />
        <circle cx="45" cy="72" r="1.5" fill="#3dd6ff" opacity="0.5" />
      </svg>
      <p className="mt-1 text-center font-mono text-[9px] uppercase tracking-widest text-hud-cyan/50">
        Local ping
      </p>
    </div>
  );
}
