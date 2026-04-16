"use client";
import { useState, useCallback, useEffect } from "react";
import useSWR from "swr";
import type { AircraftState } from "@/lib/types";
import { apiFetch } from "@/lib/api";
import { generateMockAircraft } from "@/lib/mockData";
import { getWsOrigin } from "@/lib/ws";
import { useWebSocket } from "./useWebSocket";

export function useAircraftData() {
  const [aircraft, setAircraft] = useState<AircraftState[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setAircraft(generateMockAircraft());
  }, []);

  const onMessage = useCallback((data: unknown) => {
    if (Array.isArray(data)) {
      setAircraft(data);
      setWsConnected(true);
    }
  }, []);

  const { connected } = useWebSocket({
    url: `${getWsOrigin()}/ws/aircraft`,
    onMessage,
  });

  useSWR(
    connected ? null : "/aircraft/live",
    (path) => apiFetch<AircraftState[]>(path),
    {
      refreshInterval: 5000,
      onSuccess: (data) => {
        if (!connected) setAircraft(data);
      },
      onError: () => {
        if (aircraft.length === 0) setAircraft(generateMockAircraft());
      },
    }
  );

  if (!mounted) {
    return { aircraft: [], connected: false, live: false };
  }

  return { aircraft, connected: connected || wsConnected, live: connected };
}
