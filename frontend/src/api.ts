import type { Answer, Comparison, DocInfo, Overview } from "./types";

export const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, init);
  } catch {
    throw new Error("Cannot reach the server. Check your connection and try again.");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (res.status === 422) detail = "That input was not valid.";
    } catch { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

export const uploadDocument = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<DocInfo>("/api/documents", { method: "POST", body: form });
};
export const loadSample = (key: "a" | "b") => request<DocInfo>(`/api/documents/sample/${key}`, { method: "POST" });
export const getOverview = (id: string) => request<Overview>(`/api/documents/${id}/overview`);
export const ask = (id: string, question: string, history: { q: string; a: string }[]) =>
  request<Answer>(`/api/documents/${id}/ask`, json({ question, history }));
export const compare = (docA: string, docB: string, aspects: string[]) =>
  request<Comparison>("/api/compare", json({ doc_a: docA, doc_b: docB, aspects }));
export const pdfUrl = (id: string, page: number) => `${API}/api/documents/${id}/pdf#page=${page}&view=FitH`;
export const reportUrl = (id: string) => `${API}/api/documents/${id}/report`;
