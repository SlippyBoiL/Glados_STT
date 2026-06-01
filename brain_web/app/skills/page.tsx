"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Skill } from "@/lib/types";

const categoryLabels: Record<string, string> = {
  server: "Server / SSH",
  messaging: "Messaging",
  meta: "Self-repair / Meta",
  general: "General",
  learned: "Self-learned",
};

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    api.skills().then((r) => setSkills(r.skills));
  }, []);

  const grouped = skills.reduce<Record<string, Skill[]>>((acc, s) => {
    const cat = s.category || "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Protocol Registry</h2>
        <p className="text-sm text-aperture-muted">
          Learned protocols from data/glados_skills_brain.json (self-developed)
        </p>
      </div>

      {Object.entries(grouped).map(([cat, list]) => (
        <div key={cat} className="panel p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase text-aperture-orange">
            {categoryLabels[cat] || cat} ({list.length})
          </h3>
          <div className="grid gap-2 md:grid-cols-2">
            {list.map((s) => (
              <div
                key={s.file}
                className="rounded border border-aperture-border/60 bg-black/20 px-3 py-2"
              >
                <p className="font-mono text-sm text-aperture-blue">{s.id || s.file}</p>
                <p className="mt-1 text-sm text-aperture-muted">
                  {s.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      ))}

      {skills.length === 0 ? (
        <p className="text-aperture-muted">No skills found.</p>
      ) : null}
    </div>
  );
}
