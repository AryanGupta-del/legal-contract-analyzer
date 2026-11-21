import { useEffect, useRef, useState } from "react";
import { Bot, FileText, Send, User } from "lucide-react";
import { ask } from "../api";
import type { ChatMessage, Source } from "../types";
import { cx, ErrorBanner, Spinner } from "./ui";

const SUGGESTIONS = [
  "Can I cancel early, and what does it cost?",
  "Who is liable if something goes wrong?",
  "Does the contract renew automatically?",
  "What are the payment terms?",
];

function AnswerText({ text, sources, onJump }: { text: string; sources: Source[]; onJump: (page: number) => void }) {
  return (
    <p className="whitespace-pre-wrap leading-relaxed">
      {text.split(/(\[\d+\])/g).map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        const src = m && sources.find((s) => s.n === Number(m[1]));
        return src ? (
          <button key={i} onClick={() => onJump(src.page)} title={`Page ${src.page} · ${src.label}`}
            className="mx-0.5 inline-grid h-5 min-w-5 place-items-center rounded-md bg-brand-100 px-1 align-text-top text-[11px] font-bold text-brand-700 hover:bg-brand-600 hover:text-white">
            {src.n}
          </button>
        ) : <span key={i}>{part}</span>;
      })}
    </p>
  );
}

export default function Ask({ docId, onJump }: { docId: string; onJump: (page: number) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, busy]);

  async function send(question: string) {
    const q = question.trim();
    if (q.length < 2 || busy) return;
    const history: { q: string; a: string }[] = [];
    for (let i = 0; i + 1 < messages.length; i += 2) history.push({ q: messages[i].text, a: messages[i + 1].text });
    setMessages((m) => [...m, { role: "user", text: q }]);
    setDraft(""); setError(""); setBusy(true);
    try {
      const res = await ask(docId, q, history.slice(-3));
      setMessages((m) => [...m, { role: "assistant", text: res.answer, sources: res.sources, found: res.found }]);
    } catch (e) {
      setMessages((m) => m.slice(0, -1)); // drop the unanswered question so pairs stay aligned
      setDraft(q); setError((e as Error).message);
    } finally { setBusy(false); }
  }

  return (
    <div className="flex min-h-[28rem] flex-col">
      <div className="flex-1 space-y-5 pb-4">
        {messages.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center">
            <p className="font-medium text-slate-800">Ask anything about this contract</p>
            <p className="mt-1 text-sm text-slate-500">Answers come only from the document and cite the clause they used.</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => void send(s)}
                  className="rounded-full bg-brand-50 px-3.5 py-1.5 text-sm text-brand-700 hover:bg-brand-100">{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cx("rise flex gap-3", m.role === "user" && "flex-row-reverse")}>
            <span className={cx("grid h-8 w-8 shrink-0 place-items-center rounded-full", m.role === "user" ? "bg-slate-800 text-white" : "bg-brand-600 text-white")}>
              {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </span>
            <div className={cx("max-w-[85%] rounded-2xl px-4 py-3 text-sm",
              m.role === "user" ? "bg-slate-800 text-white" : "border border-slate-200 bg-white text-slate-800 shadow-sm")}>
              {m.role === "user" ? m.text : (
                <>
                  <AnswerText text={m.text} sources={m.sources ?? []} onJump={onJump} />
                  {m.found === false && <p className="mt-2 text-xs text-amber-700">Not found in the contract text.</p>}
                  {!!m.sources?.length && (
                    <div className="mt-3 space-y-1.5 border-t border-slate-100 pt-3">
                      {m.sources.map((s) => (
                        <button key={s.n} onClick={() => onJump(s.page)}
                          className="block w-full rounded-lg bg-slate-50 p-2.5 text-left hover:bg-brand-50">
                          <span className="flex items-center gap-1.5 text-xs font-semibold text-brand-700">
                            <FileText className="h-3.5 w-3.5" /> [{s.n}] Page {s.page} · {s.label}
                          </span>
                          <span className="mt-1 line-clamp-2 text-xs text-slate-600">{s.text}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-3 text-sm text-slate-500"><Spinner className="h-4 w-4 text-brand-600" /> Searching the contract…</div>
        )}
        {error && <ErrorBanner message={error} />}
        <div ref={end} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); void send(draft); }}
        className="sticky bottom-0 flex gap-2 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent pb-1 pt-3">
        <input value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={500} placeholder="Ask about termination, liability, payment…"
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20" />
        <button type="submit" disabled={busy || draft.trim().length < 2} aria-label="Send"
          className="grid w-12 place-items-center rounded-xl bg-brand-600 text-white shadow-sm hover:bg-brand-700 disabled:opacity-40">
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
