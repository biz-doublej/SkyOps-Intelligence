"use client";
import { Plane, AlertTriangle, Clock, Activity } from "lucide-react";
import MetricCard from "@/components/shared/MetricCard";
import Card from "@/components/shared/Card";
import { useAircraftData } from "@/hooks/useAircraftData";
import { useAnomalyFeed } from "@/hooks/useAnomalyFeed";
import { formatDistanceToNow } from "date-fns";
import { ko } from "date-fns/locale";
import { SEVERITY_COLORS } from "@/lib/constants";

export default function DashboardPage() {
  const { aircraft, connected } = useAircraftData();
  const { events } = useAnomalyFeed();
  const highSeverity = events.filter((e) => e.severity === "HIGH").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">대시보드</h1>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`}
          />
          {connected ? "실시간 연결" : "오프라인 (Mock)"}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="추적 항공기"
          value={aircraft.length}
          icon={<Plane className="w-5 h-5" />}
          color="text-sky-400"
          sub="현재 모니터링 중"
        />
        <MetricCard
          label="이상 탐지"
          value={events.length}
          icon={<AlertTriangle className="w-5 h-5" />}
          color="text-amber-400"
          sub={`HIGH ${highSeverity}건`}
        />
        <MetricCard
          label="평균 고도"
          value={`${Math.round(aircraft.reduce((s, a) => s + a.baro_altitude, 0) / (aircraft.length || 1))}m`}
          icon={<Activity className="w-5 h-5" />}
          color="text-emerald-400"
        />
        <MetricCard
          label="평균 속도"
          value={`${Math.round(aircraft.reduce((s, a) => s + a.velocity, 0) / (aircraft.length || 1))}m/s`}
          icon={<Clock className="w-5 h-5" />}
          color="text-purple-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="최근 이상 탐지 알림">
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {events.slice(0, 8).map((e, i) => (
              <div
                key={`${e.icao24}-${e.detected_at}-${i}`}
                className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/50"
              >
                <div
                  className="w-1 h-10 rounded-full"
                  style={{ background: SEVERITY_COLORS[e.severity] }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold">{e.callsign}</span>
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded font-bold"
                      style={{
                        color: SEVERITY_COLORS[e.severity],
                        background: `${SEVERITY_COLORS[e.severity]}20`,
                      }}
                    >
                      {e.severity}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">{e.description}</p>
                </div>
                <span className="text-[10px] text-slate-500 whitespace-nowrap">
                  {formatDistanceToNow(e.detected_at > 1e12 ? e.detected_at : e.detected_at * 1000, { addSuffix: true, locale: ko })}
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card title="항공기 상태 요약">
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {aircraft.slice(0, 10).map((a) => (
              <div key={a.icao24} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50">
                <div>
                  <span className="font-mono text-sm font-semibold">{a.callsign || a.icao24}</span>
                  <p className="text-xs text-slate-400">
                    고도 {Math.round(a.baro_altitude)}m | 속도 {Math.round(a.velocity)}m/s
                  </p>
                </div>
                <span className={`text-xs ${a.on_ground ? "text-amber-400" : "text-emerald-400"}`}>
                  {a.on_ground ? "지상" : "비행 중"}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
