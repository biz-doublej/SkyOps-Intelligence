import { clsx } from "clsx";
import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
}

export default function Card({ children, className, title }: CardProps) {
  return (
    <div
      className={clsx(
        "rounded-xl bg-[#1e293b] border border-slate-700/50 p-5",
        className
      )}
    >
      {title && (
        <h3 className="text-sm font-semibold text-slate-300 mb-3">{title}</h3>
      )}
      {children}
    </div>
  );
}
