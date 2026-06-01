"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { GraphEdge, GraphNode } from "@/lib/types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

const groupColors: Record<string, string> = {
  memory: "#34d399",
  computer: "#22d3ee",
  skill: "#c17a3a",
  intent: "#a78bfa",
  query: "#4a7fa5",
};

type Props = {
  height?: number;
};

export function MemoryGraph({ height = 420 }: Props) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [links, setLinks] = useState<{ source: string; target: string }[]>(
    [],
  );
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .graph()
      .then((g) => {
        setNodes(g.nodes);
        setLinks(
          g.edges.map((e: GraphEdge) => ({
            source: e.source,
            target: e.target,
          })),
        );
      })
      .catch((e) => setError(String(e)));
  }, []);

  const data = useMemo(
    () => ({
      nodes: nodes.map((n) => ({
        id: n.id,
        name: n.label,
        group: n.group,
        meta: n.meta,
      })),
      links,
    }),
    [nodes, links],
  );

  if (error) {
    return (
      <div className="panel p-4 text-sm text-red-400">
        Failed to load graph: {error}
      </div>
    );
  }

  return (
    <div className="panel overflow-hidden">
      <div style={{ height }}>
        {nodes.length > 0 ? (
          <ForceGraph2D
            graphData={data}
            nodeLabel="name"
            nodeColor={(n) => groupColors[(n as { group: string }).group] || "#6b7585"}
            linkColor={() => "rgba(107, 117, 133, 0.4)"}
            backgroundColor="rgba(13, 15, 18, 0)"
            onNodeClick={(n) =>
              setSelected({
                id: (n as { id: string }).id,
                label: (n as { name: string }).name,
                group: (n as { group: string }).group,
                meta: (n as { meta?: Record<string, unknown> }).meta,
              })
            }
          />
        ) : (
          <div className="flex h-full items-center justify-center text-aperture-muted">
            Loading graph…
          </div>
        )}
      </div>
      {selected ? (
        <div className="border-t border-aperture-border p-3 text-sm">
          <p className="font-semibold text-aperture-orange">{selected.label}</p>
          <p className="text-xs text-aperture-muted">{selected.group}</p>
          {selected.meta?.text ? (
            <p className="mt-2">{String(selected.meta.text)}</p>
          ) : null}
          {selected.meta?.description ? (
            <p className="mt-2">{String(selected.meta.description)}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
