"use client";
import { useState } from "react";
import { useAnomalyFeed } from "@/hooks/useAnomalyFeed";
import Card from "@/components/shared/Card";
import { formatDistanceToNow } from "date-fns";
import { ko } from "date-fns/locale";
import { SEVERITY_COLORS } from "@/lib/constants";
import { apiPost } from "@/lib/api";
import { MessageSquare } from "lucide-react";
import type { AnomalyEvent } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  ALTITUDE_SPIKE: "고도 급변",
  VELOCITY_SPIKE: "속도 이상",
  PATH_DEVIATION: "경로 이탈",
};

export default function AnomalyPage() {
  const { events, connected } = useAnomalyFeed();
  const [filter, setFilter] = useState<AnomalyEvent["severity"] | "ALL">("ALL");

  const [explaining, setExplaining] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<Record<string, string>>({});

  const explainEvent = async (e: AnomalyEvent, key: string) => {
    setExplaining(key);
    try {
      const res = await apiPost<{ explanation: string }>("/explain/anomaly", {
        callsign: e.callsign,
        anomaly_type: e.anomaly_type,
        severity: e.severity,
        description: e.description,
        altitude_m: e.altitude_m,
        velocity_m_s: e.velocity_m_s,
      });
      setExplanations((prev) => ({ ...prev, [key]: res.explanation }));
    } catch {
      setExplanations((prev) => ({ ...prev, [key]: "설명 생성 실패. vLLM 서버를 확인하세요." }));
    } finally { setExplaining(null); }
  };

  const filtered =
    filter === "ALL" ? events : events.filter((e) => e.severity === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">이상 탐지 알림</h1>
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`} />
          {connected ? "실시간" : "오프라인"}
        </div>
      </div>

      <div className="flex gap-2">
        {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filter === s
                ? "bg-sky-500/20 text-sky-400"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {s === "ALL" ? `전체 (${events.length})` : `${s} (${events.filter((e) => e.severity === s).length})`}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.map((e, i) => (
          <Card key={`${e.icao24}-${e.detected_at}-${i}`}>
            <div className="flex items-start gap-4">
              <div
                className="w-1.5 h-16 rounded-full flex-shrink-0"
                style={{ background: SEVERITY_COLORS[e.severity] }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-base font-bold">
                    {e.callsign}
                  </span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded font-bold"
                    style={{
                      color: SEVERITY_COLORS[e.severity],
                      background: `${SEVERITY_COLORS[e.severity]}20`,
                    }}
                  >
                    {e.severity}
                  </span>
                  <span className="text-xs text-slate-500 px-2 py-0.5 bg-slate-800 rounded">
                    {TYPE_LABELS[e.anomaly_type] || e.anomaly_type}
                  </span>
                </div>
                <p className="text-sm text-slate-300">{e.description}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                  <span>고도 {Math.round(e.altitude_m)}m</span>
                  <span>속도 {Math.round(e.velocity_m_s)}m/s</span>
                  <span>
                    위치 {e.latitude?.toFixed(2)}, {e.longitude?.toFixed(2)}
                  </span>
                  <button
                    onClick={() => explainEvent(e, `${e.icao24}-${e.detected_at}-${i}`)}
                    disabled={explaining === `${e.icao24}-${e.detected_at}-${i}`}
                    className="flex items-center gap-1 px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 disabled:opacity-50 ml-auto"
                  >
                    <MessageSquare className="w-3 h-3" />
                    {explaining === `${e.icao24}-${e.detected_at}-${i}` ? "분석 중..." : "AI 분석"}
                  </button>
                </div>
                {explanations[`${e.icao24}-${e.detected_at}-${i}`] && (
                  <div className="mt-2 p-3 rounded-lg bg-sky-500/5 border border-sky-500/20 text-xs text-slate-300 whitespace-pre-wrap">
                    {explanations[`${e.icao24}-${e.detected_at}-${i}`]}
                  </div>
                )}
              </div>
              <span className="text-xs text-slate-500 whitespace-nowrap">
                {formatDistanceToNow(e.detected_at > 1e12 ? e.detected_at : e.detected_at * 1000, {
                  addSuffix: true,
                  locale: ko,
                })}
              </span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
