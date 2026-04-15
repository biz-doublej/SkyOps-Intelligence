"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Map,
  AlertTriangle,
  Clock,
  Layers,
  MessageSquare,
  Plane,
  ScrollText,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "대시보드", icon: LayoutDashboard },
  { href: "/map", label: "실시간 지도", icon: Map },
  { href: "/anomaly", label: "이상 탐지", icon: AlertTriangle },
  { href: "/notam", label: "NOTAM (실시간)", icon: ScrollText },
  { href: "/predict", label: "지연 예측", icon: Clock },
  { href: "/heatmap", label: "혼잡도 맵", icon: Layers },
  { href: "/chat", label: "AI 어시스턴트", icon: MessageSquare },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-60 flex flex-col bg-[#0c1222] border-r border-slate-800">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-slate-800">
        <Plane className="w-6 h-6 text-sky-400" />
        <span className="font-bold text-lg tracking-tight">SkyOps</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                active
                  ? "bg-sky-500/15 text-sky-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              )}
            >
              <Icon className="w-4.5 h-4.5" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-slate-800 text-xs text-slate-500">
        SkyOps Intelligence v1.0
      </div>
    </aside>
  );
}
