import { ArrowRight } from "lucide-react";
import type { DocInfo, Overview as OverviewData } from "../types";
import { Card, Gauge, SeverityBadge, Skeleton } from "./ui";

export function OverviewSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}</div>
      <div className="grid gap-4 lg:grid-cols-5"><Skeleton className="h-80 lg:col-span-3" /><Skeleton className="h-80 lg:col-span-2" /></div>
      <p className="text-center text-sm text-slate-500">Reviewing every clause. This usually takes 5–15 seconds…</p>
    </div>
  );
}

function Kpi({ value, label }: { value: number | string; label: string }) {
  return (
    <Card className="px-4 py-3">
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
    </Card>
  );
}

export default function Overview({ doc, data, onSeeRisks, onJump }: {
  doc: DocInfo; data: OverviewData; onSeeRisks: () => void; onJump: (page: number) => void;
}) {
  const t = data.key_terms;
  const rows: [string, string][] = [
    ["Parties", t.parties.join(", ") || "Not specified"], ["Effective date", t.effective_date], ["Term", t.term],
    ["Renewal", t.renewal], ["Termination", t.termination], ["Notice period", t.notice_period],
    ["Payment", t.payment_terms], ["Liability cap", t.liability_cap], ["Governing law", t.governing_law],
  ];
  const top = data.risks.slice(0, 3);
  return (
    <div className="rise space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi value={doc.pages} label="Pages" />
        <Kpi value={doc.clauses} label="Clauses indexed" />
        <Kpi value={data.counts.high} label="High risks" />
        <Kpi value={data.risks.length} label="Total flags" />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="p-5 lg:col-span-3">
          <h3 className="mb-2 font-semibold text-slate-900">Key terms</h3>
          <dl className="divide-y divide-slate-100">
            {rows.map(([k, v]) => (
              <div key={k} className="flex gap-4 py-2.5 text-sm">
                <dt className="w-32 shrink-0 text-slate-500">{k}</dt>
                <dd className={v === "Not specified" ? "text-slate-400" : "font-medium text-slate-800"}>{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card className="p-5 lg:col-span-2">
          <h3 className="mb-3 font-semibold text-slate-900">Exposure score</h3>
          <Gauge score={data.score} />
          <p className="mt-3 text-center text-xs text-slate-500">Weighted count of flagged risks. A guide, not a legal opinion.</p>
          {data.summary && <p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm leading-relaxed text-slate-700">{data.summary}</p>}
        </Card>
      </div>
      {top.length > 0 && (
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">Top risks</h3>
            <button onClick={onSeeRisks} className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700">
              See all <ArrowRight className="h-4 w-4" />
            </button>
          </div>
          <ul className="space-y-2">
            {top.map((r) => (
              <li key={r.title}>
                <button onClick={() => r.clause && onJump(r.clause.page)}
                  className="flex w-full items-center gap-3 rounded-xl p-2 text-left text-sm hover:bg-slate-50">
                  <SeverityBadge severity={r.severity} />
                  <span className="flex-1 font-medium text-slate-800">{r.title}</span>
                  {r.clause && <span className="text-xs text-slate-500">p.{r.clause.page}</span>}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
