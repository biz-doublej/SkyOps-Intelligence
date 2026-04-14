"use client";
import { useState } from "react";
import Card from "@/components/shared/Card";
import { apiPost } from "@/lib/api";
import { KOREAN_AIRLINES, KOREAN_AIRPORTS, RISK_COLORS } from "@/lib/constants";
import type { DelayRequest, DelayResponse } from "@/lib/types";

const defaultForm: DelayRequest = {
  dep_hour: 14,
  dep_minute: 30,
  dep_dayofweek: 1,
  dep_month: 4,
  dep_dayofyear: 95,
  is_weekend: 0,
  distance_miles: 200,
  sched_elapsed_min: 75,
  prev_dep_delay_min: 5,
  prev_arr_delay_min: 3,
  is_prev_delayed: 0,
  origin_hourly_departures: 25,
  dest_hourly_arrivals: 20,
  dep_month_weather_score: 0.3,
  origin_weather_hist_delay: 5.2,
  dest_weather_hist_delay: 4.1,
  carrier_hist_delay: 8.5,
  origin_hist_delay: 6.3,
  dest_hist_delay: 5.8,
  route_hist_delay: 7.2,
  // Rotation features (P1 · 2026-04-14) — defaults for "first leg of day, 1hr turnaround"
  rotation_depth: 0,
  prev_leg_arr_delay_min: 0,
  scheduled_turnaround_min: 60,
  actual_turnaround_min: 60,
  is_first_leg_of_day: 1,
  carrier_code: "KE",
  origin: "ICN",
  dest: "CJU",
};

export default function PredictPage() {
  const [form, setForm] = useState(defaultForm);
  const [result, setResult] = useState<DelayResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (key: keyof DelayRequest, value: string | number) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await apiPost<DelayResponse>("/predict/delay", form);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "예측 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">지연 예측</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="비행 정보 입력">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs text-slate-400">항공사</span>
                <select
                  value={form.carrier_code}
                  onChange={(e) => update("carrier_code", e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                >
                  {Object.entries(KOREAN_AIRLINES).map(([code, name]) => (
                    <option key={code} value={code}>{code} - {name}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs text-slate-400">출발 시간</span>
                <input
                  type="number"
                  value={form.dep_hour}
                  onChange={(e) => update("dep_hour", +e.target.value)}
                  min={0} max={23}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                />
              </label>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs text-slate-400">출발 공항</span>
                <select
                  value={form.origin}
                  onChange={(e) => update("origin", e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                >
                  {Object.entries(KOREAN_AIRPORTS).map(([code, name]) => (
                    <option key={code} value={code}>{code} - {name}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs text-slate-400">도착 공항</span>
                <select
                  value={form.dest}
                  onChange={(e) => update("dest", e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                >
                  {Object.entries(KOREAN_AIRPORTS).map(([code, name]) => (
                    <option key={code} value={code}>{code} - {name}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs text-slate-400">비행 거리 (mi)</span>
                <input
                  type="number"
                  value={form.distance_miles}
                  onChange={(e) => update("distance_miles", +e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                />
              </label>
              <label className="space-y-1">
                <span className="text-xs text-slate-400">직전편 지연 (분)</span>
                <input
                  type="number"
                  value={form.prev_dep_delay_min}
                  onChange={(e) => update("prev_dep_delay_min", +e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                />
              </label>
            </div>

            <details className="mt-2 bg-slate-800/40 rounded-lg border border-slate-700/50">
              <summary className="cursor-pointer px-3 py-2 text-xs text-slate-300 font-semibold tracking-wide uppercase hover:text-slate-100">
                고급 · Rotation Features (P1 · 2026-04-14)
              </summary>
              <div className="px-3 pb-3 pt-1 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <label className="space-y-1">
                    <span className="text-xs text-slate-400">당일 leg 순서 (0=첫째)</span>
                    <input
                      type="number"
                      min={0}
                      value={form.rotation_depth ?? 0}
                      onChange={(e) => update("rotation_depth", +e.target.value)}
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs text-slate-400">직전 leg 도착 지연 (분)</span>
                    <input
                      type="number"
                      value={form.prev_leg_arr_delay_min ?? 0}
                      onChange={(e) =>
                        update("prev_leg_arr_delay_min", +e.target.value)
                      }
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <label className="space-y-1">
                    <span className="text-xs text-slate-400">예정 turnaround (분)</span>
                    <input
                      type="number"
                      value={form.scheduled_turnaround_min ?? 60}
                      onChange={(e) =>
                        update("scheduled_turnaround_min", +e.target.value)
                      }
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-xs text-slate-400">실제 turnaround (분)</span>
                    <input
                      type="number"
                      value={form.actual_turnaround_min ?? 60}
                      onChange={(e) =>
                        update("actual_turnaround_min", +e.target.value)
                      }
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  같은 기체 (tail_number) 의 연속 leg 정보. 모두 optional, 기본값은
                  &ldquo;당일 첫 leg · 1시간 turnaround&rdquo; 시나리오.
                </p>
              </div>
            </details>

            <button
              onClick={submit}
              disabled={loading}
              className="w-full bg-sky-500 hover:bg-sky-600 disabled:bg-slate-600 text-white font-semibold py-2.5 rounded-lg transition-colors"
            >
              {loading ? "예측 중..." : "지연 예측 실행"}
            </button>
            {error && <p className="text-red-400 text-sm">{error}</p>}
          </div>
        </Card>

        <Card title="예측 결과">
          {result ? (
            <div className="space-y-6">
              <div className="text-center py-4">
                <div
                  className="text-5xl font-bold"
                  style={{
                    color: result.is_delayed
                      ? RISK_COLORS.critical
                      : RISK_COLORS.normal,
                  }}
                >
                  {result.predicted_delay_min.toFixed(1)}분
                </div>
                <div
                  className="text-lg font-semibold mt-2"
                  style={{
                    color: result.is_delayed
                      ? RISK_COLORS.critical
                      : RISK_COLORS.normal,
                  }}
                >
                  {result.is_delayed ? "지연 예상" : "정상 운항 예상"}
                </div>
              </div>
              {result.prediction_interval && (
                <div className="bg-slate-800/60 rounded-lg p-4 border border-blue-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-300 text-xs font-semibold uppercase tracking-wide">
                      예측 신뢰구간 · Conformal Prediction
                    </span>
                    <span className="text-blue-300 text-xs font-mono">
                      {(result.prediction_interval.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2 justify-center py-1">
                    <span className="text-slate-400 text-sm">
                      {result.prediction_interval.lower_min.toFixed(1)}분
                    </span>
                    <span className="text-slate-500">~</span>
                    <span className="text-slate-400 text-sm">
                      {result.prediction_interval.upper_min.toFixed(1)}분
                    </span>
                  </div>
                  <div className="text-center text-xs text-slate-500 mt-1">
                    범위 {result.prediction_interval.width_min.toFixed(1)}분 ·{" "}
                    {result.prediction_interval.method.replace("split_conformal_mapie_v", "MAPIE v")}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-slate-800 rounded-lg p-3">
                  <span className="text-slate-400 text-xs">신뢰도 (legacy)</span>
                  <div className="font-semibold capitalize">{result.confidence}</div>
                </div>
                <div className="bg-slate-800 rounded-lg p-3">
                  <span className="text-slate-400 text-xs">응답 시간</span>
                  <div className="font-semibold">{result.latency_ms.toFixed(0)}ms</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500">
              비행 정보를 입력하고 예측을 실행하세요
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
