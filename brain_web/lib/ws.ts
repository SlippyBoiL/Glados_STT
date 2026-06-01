"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TelemetryEvent } from "./types";
import { wsUrl } from "./api";

export function useLiveTelemetry(maxEvents = 200) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(wsUrl());
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 2500);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data) as TelemetryEvent;
        setEvents((prev) => [...prev.slice(-(maxEvents - 1)), ev]);
      } catch {
        /* ignore */
      }
    };
  }, [maxEvents]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, connected };
}
