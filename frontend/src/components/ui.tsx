import type { ReactNode } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { Severity } from "../types";

export const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>{children}</div>;
}

const SEV: Record<Severity, string> = {
  high: "bg-red-50 text-red-700 ring-red-600/20",
  medium: "bg-amber-50 text-amber-700 ring-amber-600/20",
  low: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
};
export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={cx("inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset", SEV[severity])}>
      {severity}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} />;
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cx("animate-spin", className ?? "h-4 w-4")} />;
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="rounded-lg bg-white px-3 py-1 text-xs font-medium text-red-700 ring-1 ring-red-200 hover:bg-red-100">
          Retry
        </button>
      )}
    </div>
  );
}

export function Gauge({ score }: { score: number }) {
  const r = 52, c = 2 * Math.PI * r;
  const color = score < 30 ? "#10b981" : score < 60 ? "#f59e0b" : "#ef4444";
  const label = score < 30 ? "Low exposure" : score < 60 ? "Moderate exposure" : "High exposure";
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 120" className="h-36 w-36 -rotate-90" role="img" aria-label={`Exposure score ${score} out of 100`}>
        <circle cx="60" cy="60" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (c * score) / 100} style={{ transition: "stroke-dashoffset .8s ease" }} />
        <text x="60" y="60" textAnchor="middle" dominantBaseline="central" transform="rotate(90 60 60)"
          className="fill-slate-900 text-[28px] font-bold">{score}</text>
      </svg>
      <div className="-mt-1 text-sm font-medium" style={{ color }}>{label}</div>
    </div>
  );
}
