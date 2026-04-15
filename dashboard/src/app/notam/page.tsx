"use client";
import { useMemo, useState } from "react";
import { AlertOctagon, AlertTriangle, Info, ShieldAlert, Plane } from "lucide-react";
import Card from "@/components/shared/Card";
import MetricCard from "@/components/shared/MetricCard";
import { useNotamFeed } from "@/hooks/useNotamFeed";
import { formatDistanceToNow } from "date-fns";
import { ko } from "date-fns/locale";
import type { NotamItem, NotamSeverity } from "@/lib/types";

const SEV_STYLE: Record<NotamSeverity, { bg: string; text: string; icon: React.ElementType }> = {
  CRITICAL: { bg: "bg-rose-500/15 border-rose-500/40", text: "text-rose-300", icon: AlertOctagon },
  WARNING:  { bg: "bg-amber-500/15 border-amber-500/40", text: "text-amber-300", icon: AlertTriangle },
  ADVISORY: { bg: "bg-sky-500/15 border-sky-500/40", text: "text-sky-300", icon: ShieldAlert },
  INFO:     { bg: "bg-slate-500/15 border-slate-500/40", text: "text-slate-300", icon: Info },
};

const SEV_ORDER: Record<NotamSeverity, number> = {
  CRITICAL: 0, WARNING: 1, ADVISORY: 2, INFO: 3,
};

function Badge({ severity }: { severity: NotamSeverity }) {
  const s = SEV_STYLE[severity];
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${s.bg} ${s.text}`}>
      <Icon className="w-3.5 h-3.5" />
      {severity}
    </span>
  );
}

function NotamRow({ n }: { n: NotamItem }) {
  const s = SEV_STYLE[n.severity];
  return (
    <div className={`p-4 rounded-lg border ${s.bg} hover:bg-opacity-25 transition-colors`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <span className="font-mono text-sm text-slate-200 font-semibold">{n.notam_number}</span>
            <Badge severity={n.severity} />
            {n.notam_class && (
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {n.notam_class}
              </span>
            )}
            {n.location_icao && (
              <span className="text-xs px-2 py-0.5 rounded bg-sky-900/50 text-sky-200 font-mono">
                {n.location_icao}
              </span>
            )}
            {n.selection_code && (
              <span className="text-xs px-2 py-0.5 rounded bg-purple-900/50 text-purple-200 font-mono">
                Q-code {n.selection_code}
              </span>
            )}
            {n._mock && (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-900/50 text-yellow-300">
                MOCK
              </span>
            )}
          </div>

          {n.text_korean && (
            <p className="text-sm text-slate-200 mb-1.5">{n.text_korean}</p>
          )}
          {n.text_english && n.text_english !== n.text_korean && (
            <p className="text-xs text-slate-400 mb-1.5">{n.text_english}</p>
          )}
          {!n.text_korean && (
            <p className="text-sm text-slate-200 font-mono mb-1.5">{n.text_raw}</p>
          )}

          <div className="flex items-center gap-3 text-xs text-slate-500 mt-2">
            {n.effective_start && (
              <span title={n.effective_start}>
                발효 {formatDistanceToNow(new Date(n.effective_start), { addSuffix: true, locale: ko })}
              </span>
            )}
            {n.effective_end && (
              <span title={n.effective_end}>
                · 종료 {formatDistanceToNow(new Date(n.effective_end), { addSuffix: true, locale: ko })}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NotamPage() {
  const [filterIcao, setFilterIcao] = useState("");
  const [filterSeverity, setFilterSeverity] = useState<NotamSeverity | "">("");

  const { notams, stats, connected } = useNotamFeed({
    location_icao: filterIcao || undefined,
    severity: filterSeverity || undefined,
  });

  // Local sort: CRITICAL → WARNING → ADVISORY → INFO, then by start time desc
  const sorted = useMemo(() => {
    return [...notams].sort((a, b) => {
      const sevDiff = SEV_ORDER[a.severity] - SEV_ORDER[b.severity];
      if (sevDiff !== 0) return sevDiff;
      const aTime = a.effective_start ? new Date(a.effective_start).getTime() : 0;
      const bTime = b.effective_start ? new Date(b.effective_start).getTime() : 0;
      return bTime - aTime;
    });
  }, [notams]);

  const counts = useMemo(() => {
    return {
      critical: notams.filter((n) => n.severity === "CRITICAL").length,
      warning:  notams.filter((n) => n.severity === "WARNING").length,
      advisory: notams.filter((n) => n.severity === "ADVISORY").length,
      info:     notams.filter((n) => n.severity === "INFO").length,
    };
  }, [notams]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">NOTAM (실시간 공지)</h1>
          <p className="text-sm text-slate-400 mt-1">
            FAA SWIM 실시간 피드 + ICAO/공항 NOTAM (P6-G · 2026-04-15)
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`}
          />
          {connected ? "실시간 연결" : "오프라인 (Mock)"}
        </div>
      </div>

      {/* Severity counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="긴급 (CRITICAL)"
          value={counts.critical}
          icon={<AlertOctagon className="w-5 h-5" />}
          color="text-rose-400"
          sub="활주로 폐쇄 등"
        />
        <MetricCard
          label="경고 (WARNING)"
          value={counts.warning}
          icon={<AlertTriangle className="w-5 h-5" />}
          color="text-amber-400"
          sub="ILS 장애 등"
        />
        <MetricCard
          label="권고 (ADVISORY)"
          value={counts.advisory}
          icon={<ShieldAlert className="w-5 h-5" />}
          color="text-sky-400"
          sub="조류 활동 등"
        />
        <MetricCard
          label="정보 (INFO)"
          value={counts.info}
          icon={<Info className="w-5 h-5" />}
          color="text-slate-300"
          sub="훈련 공지 등"
        />
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="공항 ICAO (e.g. RKSI)"
            value={filterIcao}
            onChange={(e) => setFilterIcao(e.target.value.toUpperCase())}
            className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-sky-500 font-mono"
            maxLength={4}
          />
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value as NotamSeverity | "")}
            className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
          >
            <option value="">모든 심각도</option>
            <option value="CRITICAL">긴급 (CRITICAL)</option>
            <option value="WARNING">경고 (WARNING)</option>
            <option value="ADVISORY">권고 (ADVISORY)</option>
            <option value="INFO">정보 (INFO)</option>
          </select>
          {(filterIcao || filterSeverity) && (
            <button
              onClick={() => { setFilterIcao(""); setFilterSeverity(""); }}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              필터 초기화
            </button>
          )}
          <span className="ml-auto text-xs text-slate-500">
            {sorted.length}건 · 최근 NOTAM 우선 표시
          </span>
        </div>
      </Card>

      {/* Per-airport breakdown */}
      {stats && stats.by_airport.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <Plane className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold">공항별 NOTAM 분포 (top {Math.min(stats.by_airport.length, 8)})</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {stats.by_airport.slice(0, 8).map((a) => (
              <button
                key={a.airport}
                onClick={() => setFilterIcao(a.airport)}
                className={`p-2 rounded border text-left hover:border-sky-500 transition-colors ${
                  filterIcao === a.airport ? "bg-sky-500/15 border-sky-500" : "border-slate-700"
                }`}
              >
                <div className="font-mono text-sm text-slate-200">{a.airport}</div>
                <div className="text-xs text-slate-400 mt-0.5">{a.count}건</div>
                {a.critical > 0 && (
                  <div className="text-xs text-rose-300 mt-0.5">긴급 {a.critical}</div>
                )}
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* NOTAM list */}
      <div className="space-y-3">
        {sorted.length === 0 ? (
          <Card>
            <div className="text-center py-12 text-slate-500">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">조건에 맞는 NOTAM이 없습니다.</p>
            </div>
          </Card>
        ) : (
          sorted.map((n) => <NotamRow key={n.notam_number} n={n} />)
        )}
      </div>
    </div>
  );
}
