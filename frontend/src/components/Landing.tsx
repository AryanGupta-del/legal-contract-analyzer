import { useRef, useState } from "react";
import { FileSearch, FileText, GitCompare, MessageSquareQuote, Scale, ShieldAlert, UploadCloud } from "lucide-react";
import { loadSample, uploadDocument } from "../api";
import type { DocInfo } from "../types";
import { cx, ErrorBanner, Spinner } from "./ui";

const MAX_MB = 10;

const FEATURES = [
  { icon: MessageSquareQuote, title: "Answers with citations", text: "Every answer links to the exact page and clause it came from, so you can verify it in seconds." },
  { icon: ShieldAlert, title: "Risk review", text: "Severity-rated red flags such as uncapped liability and auto-renewal, each with a negotiation tip." },
  { icon: GitCompare, title: "Side-by-side compare", text: "Put two contracts next to each other and see which one is riskier, clause by clause." },
];
const STEPS = ["Upload a PDF", "Clauses are indexed", "Hybrid search finds the right text", "The model answers only from it"];

export default function Landing({ onReady }: { onReady: (d: DocInfo) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function run(job: () => Promise<DocInfo>) {
    setBusy(true); setError("");
    try { onReady(await job()); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function pick(file?: File) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) return setError("Please choose a PDF file.");
    if (file.size > MAX_MB * 1024 * 1024) return setError(`File is larger than ${MAX_MB} MB.`);
    void run(() => uploadDocument(file));
  }

  return (
    <div className="min-h-full bg-gradient-to-b from-brand-50 via-slate-50 to-slate-50">
      <header className="mx-auto flex max-w-6xl items-center gap-2 px-6 py-5">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white"><Scale className="h-5 w-5" /></span>
        <span className="font-semibold tracking-tight">Contract Analyzer</span>
      </header>

      <main className="mx-auto max-w-4xl px-6 pb-20 pt-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Understand any contract <span className="bg-gradient-to-r from-brand-600 to-violet-500 bg-clip-text text-transparent">in minutes</span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">
          Upload a PDF. Get the key terms, a risk review and plain-English answers, each backed by the clause it came from.
        </p>

        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
          className={cx("mx-auto mt-10 max-w-2xl rounded-3xl border-2 border-dashed bg-white p-10 shadow-sm transition",
            drag ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:border-brand-500")}
        >
          {busy ? (
            <div className="flex flex-col items-center gap-3 py-4 text-slate-600">
              <Spinner className="h-8 w-8 text-brand-600" />
              <div className="font-medium">Reading and indexing your contract…</div>
              <div className="text-sm text-slate-500">The first request can take a few seconds while the server wakes up.</div>
            </div>
          ) : (
            <>
              <UploadCloud className="mx-auto h-10 w-10 text-brand-600" />
              <p className="mt-3 font-medium text-slate-800">Drag and drop a contract here</p>
              <p className="text-sm text-slate-500">PDF with selectable text, up to {MAX_MB} MB</p>
              <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <button onClick={() => input.current?.click()}
                  className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700">
                  Choose PDF
                </button>
                <button onClick={() => void run(() => loadSample("a"))}
                  className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50">
                  <FileText className="h-4 w-4" /> Try a sample contract
                </button>
              </div>
              <input ref={input} type="file" accept="application/pdf,.pdf" className="hidden"
                onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
            </>
          )}
        </div>
        {error && <div className="mx-auto mt-4 max-w-2xl text-left"><ErrorBanner message={error} /></div>}
        <p className="mt-3 text-xs text-slate-500">Files are processed in memory, expire after an hour and are never stored on disk.</p>

        <div className="mt-16 grid gap-4 text-left sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-600"><Icon className="h-5 w-5" /></span>
              <h3 className="mt-3 font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{text}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-sm text-slate-600">
          <FileSearch className="h-4 w-4 text-brand-600" />
          {STEPS.map((s, i) => (
            <span key={s} className="flex items-center gap-3">
              <span className="rounded-full bg-white px-3 py-1 ring-1 ring-slate-200">{i + 1}. {s}</span>
              {i < STEPS.length - 1 && <span className="text-slate-300">→</span>}
            </span>
          ))}
        </div>
        <p className="mt-10 text-xs text-slate-400">For information only. This is not legal advice.</p>
      </main>
    </div>
  );
}
