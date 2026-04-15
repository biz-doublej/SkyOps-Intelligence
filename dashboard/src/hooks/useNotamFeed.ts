"use client";
import { useState, useCallback, useEffect } from "react";
import useSWR from "swr";
import type { NotamItem, NotamStats } from "@/lib/types";
import { apiFetch } from "@/lib/api";
import { useWebSocket } from "./useWebSocket";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MAX_NOTAMS = 200;

const MOCK_NOTAMS: NotamItem[] = [
  {
    notam_number: "A1234/26",
    notam_class: "AERODROME",
    location_icao: "RKSI",
    text_raw: "RWY 15L/33R CLSD DUE TO MAINT",
    text_english: "Runway 15L/33R closed due to maintenance",
    text_korean: "활주로 15L/33R 정비 작업으로 폐쇄",
    effective_start: new Date(Date.now() - 3600000).toISOString(),
    effective_end: new Date(Date.now() + 6 * 3600000).toISOString(),
    severity: "CRITICAL",
    _mock: true,
  },
  {
    notam_number: "B0567/26",
    notam_class: "NAV",
    location_icao: "EGLL",
    selection_code: "QNDAS",
    text_raw: "ILS RWY 27L OUT OF SERVICE",
    text_english: "ILS Runway 27L out of service",
    text_korean: "활주로 27L ILS 사용 불가",
    effective_start: new Date(Date.now() - 1800000).toISOString(),
    effective_end: new Date(Date.now() + 12 * 3600000).toISOString(),
    severity: "WARNING",
    _mock: true,
  },
  {
    notam_number: "C0089/26",
    notam_class: "OPS",
    location_icao: "RKSS",
    text_raw: "BIRD ACTIVITY VICINITY ARP",
    text_english: "Bird activity reported in vicinity of airport reference point",
    text_korean: "공항 기준점 인근 조류 활동 보고",
    effective_start: new Date(Date.now() - 7200000).toISOString(),
    severity: "ADVISORY",
    _mock: true,
  },
  {
    notam_number: "D0011/26",
    notam_class: "AIRSPACE",
    location_icao: "KATL",
    text_raw: "TEMPORARY MILITARY EXERCISE FL250-FL350",
    text_english: "Temporary military exercise FL250 to FL350",
    text_korean: "FL250-FL350 임시 군 훈련",
    effective_start: new Date().toISOString(),
    severity: "INFO",
    _mock: true,
  },
];

const MOCK_STATS: NotamStats = {
  total: MOCK_NOTAMS.length,
  by_airport: [
    { airport: "RKSI", count: 1, critical: 1, warning: 0, advisory: 0, info: 0 },
    { airport: "EGLL", count: 1, critical: 0, warning: 1, advisory: 0, info: 0 },
    { airport: "RKSS", count: 1, critical: 0, warning: 0, advisory: 1, info: 0 },
    { airport: "KATL", count: 1, critical: 0, warning: 0, advisory: 0, info: 1 },
  ],
  by_class: { AERODROME: 1, NAV: 1, OPS: 1, AIRSPACE: 1 },
  by_severity: { CRITICAL: 1, WARNING: 1, ADVISORY: 1, INFO: 1 },
};

export function useNotamFeed(filters?: {
  location_icao?: string;
  severity?: string;
}) {
  const [notams, setNotams] = useState<NotamItem[]>([]);
  const [stats, setStats] = useState<NotamStats | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setNotams(MOCK_NOTAMS);
    setStats(MOCK_STATS);
  }, []);

  const onMessage = useCallback((data: unknown) => {
    if (Array.isArray(data)) {
      setNotams((prev) => [...(data as NotamItem[]), ...prev].slice(0, MAX_NOTAMS));
    }
  }, []);

  const { connected } = useWebSocket({
    url: `${WS_URL}/ws/notams`,
    onMessage,
  });

  // Build query string
  const qp = new URLSearchParams();
  qp.set("limit", "100");
  if (filters?.location_icao) qp.set("location_icao", filters.location_icao);
  if (filters?.severity) qp.set("severity", filters.severity);

  useSWR(
    connected ? null : `/notam/recent?${qp.toString()}`,
    (path) => apiFetch<NotamItem[]>(path),
    {
      refreshInterval: 10000,
      onSuccess: (data) => {
        if (!connected && data.length > 0) setNotams(data);
      },
    }
  );

  useSWR("/notam/stats", (path) => apiFetch<NotamStats>(path), {
    refreshInterval: 30000,
    onSuccess: (data) => setStats(data),
  });

  if (!mounted) {
    return { notams: [], stats: null, connected: false };
  }

  return { notams, stats, connected };
}
