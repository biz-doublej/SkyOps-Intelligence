"use client";
import { useState, useCallback, useEffect } from "react";
import useSWR from "swr";
import type { AnomalyEvent } from "@/lib/types";
import { apiFetch } from "@/lib/api";
import { generateMockAnomalies } from "@/lib/mockData";
import { getWsOrigin } from "@/lib/ws";
import { useWebSocket } from "./useWebSocket";

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
    url: `${getWsOrigin()}/ws/anomalies`,
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
