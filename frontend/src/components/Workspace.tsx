import { useCallback, useEffect, useState } from "react";
import { Download, FileText, GitCompare, LayoutDashboard, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, Scale, ShieldAlert } from "lucide-react";
import { getOverview, reportUrl } from "../api";
import type { DocInfo, Overview as OverviewData } from "../types";
import Ask from "./Ask";
import Compare from "./Compare";
import Overview, { OverviewSkeleton } from "./Overview";
import PdfPane from "./PdfPane";
import Risks from "./Risks";
import { cx, ErrorBanner } from "./ui";

type Tab = "overview" | "risks" | "ask" | "compare";

export default function Workspace({ doc, onReset }: { doc: DocInfo; onReset: () => void }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [showPdf, setShowPdf] = useState(true);

  const load = useCallback(() => {
    setError(""); setData(null);
    getOverview(doc.id).then(setData).catch((e: Error) => setError(e.message));
  }, [doc.id]);
  useEffect(load, [load]);

  const jump = (p: number) => { setPage(p); setShowPdf(true); };
  const tabs: { id: Tab; label: string; icon: typeof Scale; badge?: number }[] = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "risks", label: "Risks", icon: ShieldAlert, badge: data?.risks.length },
    { id: "ask", label: "Ask", icon: MessageSquare },
    { id: "compare", label: "Compare", icon: GitCompare },
  ];
  const pending = (child: React.ReactNode) =>
    error ? <ErrorBanner message={error} onRetry={load} /> : data ? child : <OverviewSkeleton />;

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white"><Scale className="h-4 w-4" /></span>
        <span className="hidden font-semibold tracking-tight sm:block">Contract Analyzer</span>
        <span className="mx-1 hidden h-5 w-px bg-slate-200 sm:block" />
        <span className="flex min-w-0 items-center gap-1.5 text-sm text-slate-600"><FileText className="h-4 w-4 shrink-0" /><span className="truncate">{doc.name}</span></span>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setShowPdf(!showPdf)} className="hidden items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 md:inline-flex">
            {showPdf ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />} Document
          </button>
          <a href={reportUrl(doc.id)} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100">
            <Download className="h-4 w-4" /><span className="hidden sm:inline">Export</span>
          </a>
          <button onClick={onReset} className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700">
            <Plus className="h-4 w-4" /><span className="hidden sm:inline">New contract</span>
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {showPdf && <aside className="hidden w-1/2 max-w-[46rem] shrink-0 border-r border-slate-200 md:block"><PdfPane id={doc.id} name={doc.name} page={page} /></aside>}
        <main className="min-w-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-4 py-5">
            <nav className="mb-5 flex gap-1 rounded-xl bg-slate-200/60 p-1" role="tablist">
              {tabs.map(({ id, label, icon: Icon, badge }) => (
                <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
                  className={cx("flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition",
                    tab === id ? "bg-white text-brand-700 shadow-sm" : "text-slate-600 hover:text-slate-900")}>
                  <Icon className="h-4 w-4" /><span>{label}</span>
                  {!!badge && <span className="rounded-full bg-brand-100 px-1.5 text-[11px] font-bold text-brand-700">{badge}</span>}
                </button>
              ))}
            </nav>
            {/* tabs stay mounted so chat history and comparison results survive tab switches */}
            <div className={tab === "overview" ? "" : "hidden"}>
              {pending(data && <Overview doc={doc} data={data} onSeeRisks={() => setTab("risks")} onJump={jump} />)}
            </div>
            <div className={tab === "risks" ? "" : "hidden"}>{pending(data && <Risks data={data} onJump={jump} />)}</div>
            <div className={tab === "ask" ? "" : "hidden"}><Ask docId={doc.id} onJump={jump} /></div>
            <div className={tab === "compare" ? "" : "hidden"}><Compare docA={doc} /></div>
          </div>
        </main>
      </div>
    </div>
  );
}
