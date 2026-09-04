"use client";

import { MemoryGraph } from "@/components/MemoryGraph";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { StaticFact } from "@/lib/types";

type HonchoSnapshot = {
  enabled?: boolean;
  ready?: boolean;
  url?: string;
  workspace?: string;
  error?: string;
  user_card?: string;
  user_profile?: string;
  computer_profile?: string;
};

export default function MemoryPage() {
  const [facts, setFacts] = useState<StaticFact[]>([]);
  const [computerFacts, setComputerFacts] = useState<StaticFact[]>([]);
  const [computerMeta, setComputerMeta] = useState<{
    fact_count: number;
    synced_at_iso: string | null;
  } | null>(null);
  const [chromaEnabled, setChromaEnabled] = useState(false);
  const [chromaCount, setChromaCount] = useState(0);
  const [honcho, setHoncho] = useState<HonchoSnapshot | null>(null);

  useEffect(() => {
    const load = () =>
      api.memories().then((m) => {
        setFacts(m.static);
        setComputerFacts(m.computer || []);
        setComputerMeta(m.computer_meta || null);
        setChromaEnabled(m.chroma_enabled);
        setChromaCount(m.chroma.length);
        setHoncho(m.honcho || null);
      });
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Memory Graph</h2>
        <p className="text-sm text-aperture-muted">
          Honcho peer profiles, static facts, skills, and retrieval links
        </p>
      </div>

      <MemoryGraph />

      <div className="panel p-4">
        <h3 className="mb-3 text-sm font-semibold uppercase text-aperture-cyan">
          Honcho profile
        </h3>
        <p className="mb-3 text-xs text-aperture-muted">
          Persistent model of you and this PC — preferences, hardware, network —
          reasoned over time instead of raw log chunks.
          {honcho?.url ? ` Server: ${honcho.url}` : ""}
          {honcho?.workspace ? ` workspace=${honcho.workspace}.` : ""}
        </p>
        {!honcho?.ready ? (
          <p className="mb-6 text-sm text-aperture-orange">
            {honcho?.error ||
              "Honcho offline. Run scripts/start_honcho.ps1 then restart the kernel."}
          </p>
        ) : (
          <div className="mb-6 space-y-3 text-sm">
            {honcho.user_card ? (
              <pre className="whitespace-pre-wrap rounded border border-cyan-900/40 bg-cyan-950/20 px-3 py-2">
                {honcho.user_card}
              </pre>
            ) : null}
            {honcho.user_profile ? (
              <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded border border-cyan-900/40 bg-black/20 px-3 py-2">
                {honcho.user_profile}
              </pre>
            ) : (
              <p className="text-aperture-muted">
                User profile is still forming — talk to GLaDOS and run a facility scan.
              </p>
            )}
            {honcho.computer_profile ? (
              <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded border border-cyan-900/40 bg-black/20 px-3 py-2">
                {honcho.computer_profile}
              </pre>
            ) : null}
          </div>
        )}

        <h3 className="mb-3 text-sm font-semibold uppercase text-aperture-cyan">
          Computer Brain ({computerMeta?.fact_count ?? computerFacts.length} facts)
        </h3>
        <p className="mb-3 text-xs text-aperture-muted">
          Full PC scan knowledge — synced to Glados memory after each facility scan.
          {computerMeta?.synced_at_iso
            ? ` Last sync: ${computerMeta.synced_at_iso}.`
            : " Run run_facility_scan.py to populate."}
        </p>
        <ul className="mb-6 max-h-[420px] space-y-2 overflow-y-auto text-sm">
          {computerFacts.length === 0 ? (
            <li className="text-aperture-muted">No computer facts yet.</li>
          ) : (
            computerFacts.map((f) => (
              <li
                key={f.id}
                className="rounded border border-cyan-900/40 bg-cyan-950/20 px-3 py-2"
              >
                <span className="font-mono text-aperture-cyan">{f.id}</span>
                {f.category ? (
                  <span className="ml-2 text-[10px] uppercase text-aperture-muted">
                    {String(f.category)}
                  </span>
                ) : null}
                <p className="mt-1">{f.text}</p>
                <p className="mt-1 text-xs text-aperture-muted">
                  {(f.keywords || []).slice(0, 12).join(", ")}
                </p>
              </li>
            ))
          )}
        </ul>

        <h3 className="mb-3 text-sm font-semibold uppercase text-aperture-muted">
          Static Facts ({facts.length})
        </h3>
        <ul className="space-y-2 text-sm">
          {facts.map((f) => (
            <li
              key={f.id}
              className="rounded border border-aperture-border/60 bg-black/20 px-3 py-2"
            >
              <span className="font-mono text-aperture-orange">{f.id}</span>
              <p className="mt-1">{f.text}</p>
              <p className="mt-1 text-xs text-aperture-muted">
                {f.keywords.join(", ")}
              </p>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-aperture-muted">
          Honcho: {honcho?.ready ? "connected" : "offline"}
          {" · "}
          Chroma dynamic memory:{" "}
          {chromaEnabled ? `${chromaCount} entries` : "disabled in config"}
        </p>
      </div>
    </div>
  );
}
