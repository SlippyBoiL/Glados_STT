"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { IntentCluster } from "@/lib/types";

export default function IntentsPage() {
  const [clusters, setClusters] = useState<IntentCluster[]>([]);

  useEffect(() => {
    api.intents().then((r) => setClusters(r.clusters));
  }, []);

  const chartData = clusters.map((c) => ({
    name: c.category.replace(/_/g, " "),
    count: c.count,
  }));

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Intent Clusters</h2>
        <p className="text-sm text-aperture-muted">
          Voice triggers from brain_data.json (omni_brain)
        </p>
      </div>

      {chartData.length > 0 ? (
        <div className="panel h-64 p-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <XAxis
                dataKey="name"
                tick={{ fill: "#6b7585", fontSize: 11 }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis tick={{ fill: "#6b7585", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#151920",
                  border: "1px solid #2a3140",
                }}
              />
              <Bar dataKey="count" fill="#c17a3a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        {clusters.map((c) => (
          <div key={c.category} className="panel p-4">
            <h3 className="font-mono text-aperture-orange">{c.category}</h3>
            <p className="mb-2 text-xs text-aperture-muted">
              {c.count} training phrases
            </p>
            <ul className="max-h-40 space-y-1 overflow-y-auto text-sm text-aperture-muted">
              {c.phrases.slice(0, 12).map((p, i) => (
                <li key={i} className="truncate">
                  &bull; {p}
                </li>
              ))}
              {c.phrases.length > 12 ? (
                <li className="text-xs">+ {c.phrases.length - 12} more</li>
              ) : null}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
