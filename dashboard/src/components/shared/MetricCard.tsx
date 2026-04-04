import { clsx } from "clsx";
import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  color?: string;
  sub?: string;
}

export default function MetricCard({ label, value, icon, color = "text-sky-400", sub }: MetricCardProps) {
  return (
    <div className="rounded-xl bg-[#1e293b] border border-slate-700/50 p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400 uppercase tracking-wider">{label}</span>
        <span className={clsx("w-5 h-5", color)}>{icon}</span>
      </div>
      <div className={clsx("text-2xl font-bold", color)}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}
