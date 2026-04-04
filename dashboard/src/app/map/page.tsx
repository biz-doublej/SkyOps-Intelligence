"use client";
import dynamic from "next/dynamic";
import { useAircraftData } from "@/hooks/useAircraftData";

const AircraftMap = dynamic(() => import("@/components/map/AircraftMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center text-slate-400">
      지도 로딩 중...
    </div>
  ),
});

export default function MapPage() {
  const { aircraft, connected, live } = useAircraftData();

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">실시간 항공기 지도</h1>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-400">
            항공기 {aircraft.length}대 추적 중
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                live ? "bg-green-400 animate-pulse" : connected ? "bg-amber-400" : "bg-red-400"
              }`}
            />
            <span className="text-xs text-slate-500">
              {live ? "WebSocket" : connected ? "Polling" : "Mock"}
            </span>
          </span>
        </div>
      </div>
      <div className="flex-1 rounded-xl overflow-hidden border border-slate-700/50">
        <AircraftMap aircraft={aircraft} />
      </div>
    </div>
  );
}
