import { useState } from "react";
import { CheckCircle2, ChevronDown, ExternalLink, Lightbulb } from "lucide-react";
import type { Overview, Risk, Severity } from "../types";
import { Card, cx, SeverityBadge } from "./ui";

const BORDER: Record<Severity, string> = { high: "border-l-red-500", medium: "border-l-amber-400", low: "border-l-emerald-400" };
const FILTERS: ("all" | Severity)[] = ["all", "high", "medium", "low"];

function RiskCard({ risk, onJump }: { risk: Risk; onJump: (page: number) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className={cx("rise border-l-4 p-5", BORDER[risk.severity])}>
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={risk.severity} />
        <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-[11px] font-medium text-brand-700">{risk.category}</span>
        <span className="text-xs text-slate-500">Affects: {risk.party_affected}</span>
        {risk.clause && (
          <button onClick={() => onJump(risk.clause!.page)}
            className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700">
            Page {risk.clause.page} · {risk.clause.label} <ExternalLink className="h-3 w-3" />
          </button>
        )}
      </div>
      <h4 className="mt-2 font-semibold text-slate-900">{risk.title}</h4>
      <p className="mt-1 text-sm leading-relaxed text-slate-700">{risk.explanation}</p>
      {risk.recommendation && (
        <div className="mt-3 flex gap-2 rounded-xl bg-brand-50 p-3 text-sm text-brand-900">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
          <span><b>Suggested action:</b> {risk.recommendation}</span>
        </div>
      )}
      {risk.clause && (
        <>
          <button onClick={() => setOpen(!open)} className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700">
            <ChevronDown className={cx("h-3.5 w-3.5 transition", open && "rotate-180")} /> {open ? "Hide" : "Show"} clause text
          </button>
          {open && <blockquote className="mt-2 border-l-2 border-slate-200 pl-3 text-sm italic text-slate-600">{risk.clause.text}</blockquote>}
        </>
      )}
    </Card>
  );
}

export default function Risks({ data, onJump }: { data: Overview; onJump: (page: number) => void }) {
  const [filter, setFilter] = useState<"all" | Severity>("all");
  if (data.risks.length === 0) {
    return (
      <Card className="flex flex-col items-center gap-2 p-10 text-center">
        <CheckCircle2 className="h-8 w-8 text-emerald-500" />
        <p className="font-medium">No significant risks were flagged.</p>
      </Card>
    );
  }
  const shown = data.risks.filter((r) => filter === "all" || r.severity === filter);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={cx("rounded-full px-3.5 py-1.5 text-sm font-medium capitalize ring-1 ring-inset transition",
              filter === f ? "bg-brand-600 text-white ring-brand-600" : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50")}>
            {f}{f !== "all" && <span className="ml-1.5 opacity-70">{data.counts[f]}</span>}
          </button>
        ))}
      </div>
      {shown.map((r) => <RiskCard key={r.title + r.source_id} risk={r} onJump={onJump} />)}
    </div>
  );
}
