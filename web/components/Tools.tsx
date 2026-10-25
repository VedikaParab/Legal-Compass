"use client";

import { useState } from "react";
import Timeline from "./Timeline";
import { checkDate, lookupSection } from "@/lib/api";
import { GLOSSARY } from "@/lib/i18n-extra";
import type { Lang, T } from "@/lib/i18n";
import type { LawCheck, LookupResult } from "@/lib/types";

/** Quick old ↔ new section converter backed by the LegalCompass mapping. */
export function Converter({ t, lang, autoFocus = false }: { t: T; lang: Lang; autoFocus?: boolean }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<LookupResult | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async (v = q) => {
    if (!v.trim()) return;
    setQ(v); setBusy(true); setErr("");
    try { setRes(await lookupSection(v, lang)); } catch (e) { setRes(null); setErr(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); go(); }} className="flex gap-2">
        <label htmlFor="conv-q" className="sr-only">{t.conv_title}</label>
        <input id="conv-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.conv_placeholder} autoFocus={autoFocus}
          className="min-w-0 flex-1 rounded-lg border border-ink/15 bg-white px-3 py-2 text-ink placeholder:text-slate/60 focus:border-sky focus:outline-none" />
        <button type="submit" disabled={busy} className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-ink-2 disabled:opacity-50">
          {busy ? "…" : t.conv_go}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-slate">{t.conv_try}</span>
        {["420", "302", "498A", "376", "BNS 303", "CrPC 154"].map((x) => (
          <button key={x} type="button" onClick={() => go(x)} className="rounded-full bg-mist px-2.5 py-1 font-semibold text-ink-2 hover:bg-sky hover:text-white">{x}</button>
        ))}
      </div>
      {err && <p role="alert" className="mt-3 text-sm text-warn">{err}</p>}
      {res && (
        <div className="mt-4" aria-live="polite">
          {!res.found ? <p className="text-sm text-warn">{res.message}</p> : (
            <ul className="space-y-2">
              {res.results.map((r) => (
                <li key={r.row_id} className="rounded-xl border border-ink/10 bg-white p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-mist px-2 py-1 font-mono text-sm font-bold text-ink">{r.old || "—"}</span>
                    <span aria-hidden="true" className="text-amber">➜</span>
                    <span className="rounded-md bg-amber-soft px-2 py-1 font-mono text-sm font-bold text-ink">{r.new || "—"}</span>
                    <span className={`ml-auto rounded-full px-2 py-0.5 text-[11px] font-semibold ${r.change === "Y" ? "bg-amber-soft text-warn" : "bg-mist text-ok"}`}>
                      {r.change === "Y" ? t.text_changed : r.change === "N" ? t.same_law : t.check_both}
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm text-ink-2">{r.new_heading || r.old_heading}</p>
                  {!r.old && <p className="mt-1 text-xs text-warn">{t.conv_new_only}</p>}
                  {r.notes && <p className="mt-1 text-xs text-slate">{r.notes}</p>}
                </li>
              ))}
            </ul>
          )}
          {res.found && res.results.length > 1 && <p className="mt-2 text-xs text-warn">{t.split_badge}</p>}
        </div>
      )}
    </div>
  );
}

/** "Which law applies?" — pick a date and see IPC or BNS on the timeline. */
export function DateChecker({ t, lang, dark = false }: { t: T; lang: Lang; dark?: boolean }) {
  const [date, setDate] = useState("");
  const [res, setRes] = useState<LawCheck | null>(null);
  const pick = async (v: string) => {
    setDate(v); setRes(null);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return;
    try { setRes(await checkDate(v, lang)); }
    catch { setRes({ date: v, law: v < "2024-07-01" ? "IPC" : "BNS", decision: "decided", reason: null }); }
  };
  const law = res?.law ?? (date && date.length === 10 ? (date < "2024-07-01" ? "IPC" : "BNS") : null);
  return (
    <div>
      <label htmlFor="date-check" className={`text-sm font-semibold ${dark ? "text-white" : "text-ink"}`}>{t.date_q}</label>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <input id="date-check" type="date" value={date} min="1950-01-01" max={new Date().toISOString().slice(0, 10)} onChange={(e) => pick(e.target.value)}
          className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-ink focus:border-sky focus:outline-none" />
        <p aria-live="polite" className={`text-base font-bold ${law === "BNS" ? (dark ? "text-amber" : "text-ink") : law === "IPC" ? (dark ? "text-white" : "text-sky") : dark ? "text-white/70" : "text-slate"}`}>
          {law === "BNS" ? `✓ ${t.date_bns}` : law === "IPC" ? `✓ ${t.date_ipc}` : <span className="text-sm font-normal">{t.date_pick}</span>}
        </p>
      </div>
      <div className="mt-5"><Timeline t={t} date={law ? date : null} dark={dark} /></div>
      {res?.reason && <p className={`mt-3 text-xs ${dark ? "text-white/70" : "text-slate"}`}>{res.reason}</p>}
    </div>
  );
}

export function Glossary({ lang, columns = "sm:grid-cols-2 xl:grid-cols-4" }: { lang: Lang; columns?: string }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <dl className={`grid gap-3 ${columns}`}>
      {GLOSSARY[lang].map((g, i) => (
        <div key={g.term} className="rounded-xl bg-white p-4 ring-1 ring-ink/5">
          <dt>
            <button type="button" aria-expanded={open === i} onClick={() => setOpen(open === i ? null : i)}
              className="flex w-full items-center justify-between gap-2 text-left font-bold text-ink">
              {g.term}<span aria-hidden="true" className="text-amber">{open === i ? "−" : "+"}</span>
            </button>
          </dt>
          <dd className={`mt-2 text-sm leading-relaxed text-slate ${open === i ? "" : "line-clamp-2"}`}>{g.def}</dd>
        </div>
      ))}
    </dl>
  );
}
