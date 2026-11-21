export type Severity = "high" | "medium" | "low";

export interface DocInfo { id: string; name: string; pages: number; clauses: number }
export interface Clause { page: number; label: string; text: string }
export interface Risk {
  title: string; category: string; severity: Severity; party_affected: string;
  explanation: string; recommendation: string; source_id: number; clause: Clause | null;
}
export interface KeyTerms {
  parties: string[]; effective_date: string; term: string; renewal: string; termination: string;
  notice_period: string; payment_terms: string; liability_cap: string; governing_law: string;
}
export interface Overview {
  key_terms: KeyTerms; summary: string; score: number;
  counts: Record<Severity, number>; risks: Risk[];
}
export interface Source { n: number; page: number; label: string; text: string }
export interface Answer { answer: string; found: boolean; sources: Source[] }
export interface CompareRow { aspect: string; contract_a: string; contract_b: string; riskier: "a" | "b" | "similar"; note: string }
export interface Comparison { rows: CompareRow[]; verdict: string }
export interface ChatMessage { role: "user" | "assistant"; text: string; sources?: Source[]; found?: boolean }
