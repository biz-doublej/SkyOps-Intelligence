"use client";
import dynamic from "next/dynamic";

const HeatmapGL = dynamic(() => import("@/components/map/HeatmapGL"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center text-slate-400">
      히트맵 로딩 중...
    </div>
  ),
});

export default function HeatmapPage() {
  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">H3 혼잡도 히트맵</h1>
        <span className="text-xs text-slate-500">
          Mapbox GL + H3 Resolution 5 · 실시간 갱신 5초
        </span>
      </div>
      <div className="flex-1 rounded-xl overflow-hidden border border-slate-700/50">
        <HeatmapGL />
      </div>
    </div>
  );
}
