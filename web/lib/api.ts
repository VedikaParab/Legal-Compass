import type { Analysis, DocResult, LawCheck, LookupResult } from "./types";
import { DICTS, type Lang } from "./i18n";

// Empty in local development (Next forwards /api to the backend). On Vercel set NEXT_PUBLIC_API_BASE to the
// Render backend URL, e.g. https://legalcompass-backend.onrender.com — the browser then calls it directly.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "");

export class NeedsOcr extends Error {}

async function fail(r: Response, lang: Lang): Promise<never> {
  const t = DICTS[lang];
  let detail: unknown = "";
  try { detail = (await r.json()).detail; } catch { /* not JSON */ }
  if (r.status === 422 && detail && typeof detail === "object" && (detail as { code?: string }).code === "needs_ocr") throw new NeedsOcr();
  if (r.status === 422) throw new Error(typeof detail === "string" && detail ? detail : t.error_short);
  if (r.status === 429) throw new Error(typeof detail === "string" ? detail : "Too many requests — please wait a minute.");
  if (r.status >= 500) throw new Error(t.error_busy);
  throw new Error(`Error ${r.status}`);
}

export async function analyze(narrative: string, answers: Record<string, string>, finalize: boolean, lang: Lang): Promise<Analysis> {
  const r = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ narrative, answers, finalize, lang }),
  });
  if (!r.ok) await fail(r, lang);
  return r.json();
}

export async function uploadDocument(file: File, lang: Lang): Promise<DocResult> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_BASE}/api/document?lang=${lang}`, { method: "POST", body: fd });
  if (!r.ok) await fail(r, lang);
  return r.json();
}

export async function sendDocumentText(text: string, filename: string, lang: Lang, pages?: number, pagesRead?: number): Promise<DocResult> {
  const r = await fetch(`${API_BASE}/api/document-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, filename, lang, pages, pages_read: pagesRead }),
  });
  if (!r.ok) await fail(r, lang);
  return r.json();
}

export async function downloadComplaint(narrative: string, answers: Record<string, string>, kind: "fir" | "sp" | "magistrate"): Promise<void> {
  const r = await fetch(`${API_BASE}/api/complaint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ narrative, answers, kind }),
  });
  if (!r.ok) await fail(r, "en");
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url; a.download = `legalcompass-${kind}-draft.docx`; a.click();
  URL.revokeObjectURL(url);
}

export async function ping(timeoutMs = 90000): Promise<boolean> {
  const ctl = new AbortController();
  const id = setTimeout(() => ctl.abort(), timeoutMs);
  try { return (await fetch(`${API_BASE}/api/status`, { signal: ctl.signal })).ok; }
  catch { return false; }
  finally { clearTimeout(id); }
}

export async function lookupSection(q: string, lang: Lang): Promise<LookupResult> {
  const r = await fetch(`${API_BASE}/api/lookup?q=${encodeURIComponent(q)}`);
  if (!r.ok) await fail(r, lang);
  return r.json();
}

export async function checkDate(date: string, lang: Lang): Promise<LawCheck> {
  const r = await fetch(`${API_BASE}/api/applicable-law?date=${date}&lang=${lang}`);
  if (!r.ok) await fail(r, lang);
  return r.json();
}
