"use client";

import dynamic from "next/dynamic";
import { Suspense } from "react";
import type { ClusterActivity } from "@/lib/neuralState";

const NeuralCanvasInner = dynamic(() => import("./NeuralCanvasInner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-[#00050b]">
      <p className="font-mono text-xs tracking-[0.3em] text-[#00F0FF]/70">
        INITIALIZING NEURAL LATTICE…
      </p>
    </div>
  ),
});

export function NeuralBrainViewport({ activity }: { activity: ClusterActivity }) {
  return (
    <div className="relative h-full min-h-[420px] w-full overflow-hidden rounded-sm border border-[#00F0FF]/20 bg-[#00050b]">
      <div
        className="pointer-events-none absolute inset-0 z-10"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 40%, rgba(0,5,11,0.55) 100%)",
          boxShadow: "inset 0 0 60px rgba(0,240,255,0.08)",
        }}
      />
      <Suspense fallback={null}>
        <NeuralCanvasInner activity={activity} />
      </Suspense>
      <div className="pointer-events-none absolute bottom-3 left-3 z-20 font-mono text-[9px] uppercase tracking-[0.35em] text-[#00F0FF]/45">
        Drag to orbit · Scroll to zoom · Auto-rotate engaged
      </div>
    </div>
  );
}
