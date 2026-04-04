"use client";
import { useState, useCallback, useEffect } from "react";
import useSWR from "swr";
import type { AnomalyEvent } from "@/lib/types";
import { apiFetch } from "@/lib/api";
import { generateMockAnomalies } from "@/lib/mockData";
import { useWebSocket } from "./useWebSocket";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MAX_EVENTS = 100;

export function useAnomalyFeed() {
  const [events, setEvents] = useState<AnomalyEvent[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setEvents(generateMockAnomalies());
  }, []);

  const onMessage = useCallback((data: unknown) => {
    if (Array.isArray(data)) {
      setEvents((prev) => [...data, ...prev].slice(0, MAX_EVENTS));
    }
  }, []);

  const { connected } = useWebSocket({
    url: `${WS_URL}/ws/anomalies`,
    onMessage,
  });

  useSWR(
    connected ? null : "/anomaly/recent?limit=50",
    (path) => apiFetch<AnomalyEvent[]>(path),
    {
      refreshInterval: 5000,
      onSuccess: (data) => {
        if (!connected) setEvents(data);
      },
      onError: () => {
        if (events.length === 0) setEvents(generateMockAnomalies());
      },
    }
  );

  if (!mounted) {
    return { events: [], connected: false };
  }

  return { events, connected };
}
