import { useRef, useState } from "react";
import { FileText, GitCompare, UploadCloud } from "lucide-react";
import { compare, loadSample, uploadDocument } from "../api";
import type { Comparison, DocInfo } from "../types";
import { Card, cx, ErrorBanner, Spinner } from "./ui";

const ASPECTS = [
  "Term and renewal", "Termination and notice period", "Limitation of liability", "Indemnification",
  "Payment terms and fees", "Confidentiality", "Governing law and dispute resolution",
];
const LABEL = { a: "A is riskier", b: "B is riskier", similar: "Similar" } as const;
const TONE = { a: "bg-red-50 text-red-700", b: "bg-red-50 text-red-700", similar: "bg-slate-100 text-slate-600" } as const;

export default function Compare({ docA }: { docA: DocInfo }) {
  const [docB, setDocB] = useState<DocInfo | null>(null);
  const [aspects, setAspects] = useState<string[]>(ASPECTS);
  const [custom, setCustom] = useState("");
  const [result, setResult] = useState<Comparison | null>(null);
  const [busy, setBusy] = useState<"" | "upload" | "compare">("");
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  async function getB(job: () => Promise<DocInfo>) {
    setBusy("upload"); setError(""); setResult(null);
    try { setDocB(await job()); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  async function run() {
    if (!docB) return;
    setBusy("compare"); setError("");
    try {
      setResult(await compare(docA.id, docB.id, [...aspects, ...(custom.trim() ? [custom.trim()] : [])]));
    } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  const toggle = (a: string) => setAspects((s) => (s.includes(a) ? s.filter((x) => x !== a) : [...s, a]));
  const nothing = aspects.length === 0 && !custom.trim();

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-slate-50 p-3 text-sm"><div className="text-xs font-semibold text-slate-500">CONTRACT A</div>
            <div className="mt-1 flex items-center gap-2 font-medium"><FileText className="h-4 w-4 text-brand-600" />{docA.name}</div></div>
          <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm">
            <div className="text-xs font-semibold text-slate-500">CONTRACT B</div>
            {docB ? (
              <div className="mt-1 flex items-center gap-2 font-medium"><FileText className="h-4 w-4 text-brand-600" />{docB.name}
                <button onClick={() => { setDocB(null); setResult(null); }} className="ml-auto text-xs font-normal text-slate-500 underline">change</button></div>
            ) : (
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <button onClick={() => input.current?.click()} disabled={!!busy}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold ring-1 ring-slate-300 hover:bg-slate-50">
                  {busy === "upload" ? <Spinner className="h-3.5 w-3.5" /> : <UploadCloud className="h-3.5 w-3.5" />} Upload PDF</button>
                <button onClick={() => void getB(() => loadSample("b"))} disabled={!!busy}
                  className="rounded-lg px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-50">Use sample B</button>
                <input ref={input} type="file" accept="application/pdf,.pdf" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) void getB(() => uploadDocument(f)); e.target.value = ""; }} />
              </div>
            )}
          </div>
        </div>
        <div className="mt-4 text-sm font-medium text-slate-700">Aspects to compare</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {ASPECTS.map((a) => (
            <button key={a} onClick={() => toggle(a)} aria-pressed={aspects.includes(a)}
              className={cx("rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset transition",
                aspects.includes(a) ? "bg-brand-600 text-white ring-brand-600" : "bg-white text-slate-600 ring-slate-300")}>{a}</button>
          ))}
        </div>
        <input value={custom} onChange={(e) => setCustom(e.target.value)} maxLength={120} placeholder="Add your own aspect, e.g. data protection"
          className="mt-3 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20" />
        <button onClick={() => void run()} disabled={!docB || !!busy || nothing}
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40">
          {busy === "compare" ? <Spinner /> : <GitCompare className="h-4 w-4" />} Compare contracts
        </button>
      </Card>
      {error && <ErrorBanner message={error} />}
      {result && (
        <div className="rise space-y-4">
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr><th className="px-4 py-3">Aspect</th><th className="px-4 py-3">A</th><th className="px-4 py-3">B</th><th className="px-4 py-3">Riskier</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.rows.map((r) => (
                  <tr key={r.aspect} className="align-top">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.aspect}</td>
                    <td className="px-4 py-3 text-slate-700">{r.contract_a}</td>
                    <td className="px-4 py-3 text-slate-700">{r.contract_b}</td>
                    <td className="px-4 py-3">
                      <span className={cx("inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold", TONE[r.riskier])}>{LABEL[r.riskier]}</span>
                      {r.note && <div className="mt-1.5 text-xs text-slate-500">{r.note}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          {result.verdict && <Card className="bg-brand-50 p-5 text-sm text-brand-900"><b>Verdict.</b> {result.verdict}</Card>}
        </div>
      )}
    </div>
  );
}
