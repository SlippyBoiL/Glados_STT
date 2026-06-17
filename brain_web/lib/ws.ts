"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TelemetryEvent } from "./types";
import { wsUrl, api } from "./api";

export function useLiveTelemetry(maxEvents = 500) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bootstrapped = useRef(false);

  const mergeEvents = useCallback((incoming: TelemetryEvent[]) => {
    if (!incoming.length) return;
    setEvents((prev) => {
      const byKey = new Map<string, TelemetryEvent>();
      const key = (ev: TelemetryEvent) =>
        `${ev.ts}-${ev.event_type}-${JSON.stringify(ev.payload || {}).slice(0, 80)}`;
      for (const ev of prev) byKey.set(key(ev), ev);
      for (const ev of incoming) byKey.set(key(ev), ev);
      return Array.from(byKey.values())
        .sort((a, b) => a.ts - b.ts)
        .slice(-maxEvents);
    });
  }, [maxEvents]);

  const bootstrap = useCallback(async () => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    try {
      const res = await api.recent(Math.min(maxEvents, 400));
      mergeEvents(res.events || []);
    } catch {
      bootstrapped.current = false;
    }
  }, [maxEvents, mergeEvents]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    void bootstrap();

    const ws = new WebSocket(wsUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      void bootstrap();
    };
    ws.onclose = () => {
      setConnected(false);
      bootstrapped.current = false;
      setTimeout(connect, 2500);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (msg) => {
      try {
        const raw = JSON.parse(msg.data) as TelemetryEvent & {
          data?: Record<string, unknown>;
        };
        // Support both legacy { payload } and schema { data } shapes.
        if (!raw.payload && raw.data) {
          raw.payload = raw.data;
        }
        mergeEvents([raw]);
      } catch {
        /* ignore */
      }
    };
  }, [bootstrap, mergeEvents]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, connected };
}
