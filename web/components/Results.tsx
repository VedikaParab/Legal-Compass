"use client";

import { useEffect, useMemo, useState } from "react";
import Timeline from "./Timeline";
import { downloadComplaint } from "@/lib/api";
import { EVIDENCE, EVIDENCE_GROUP_OF, type EvidenceGroup } from "@/lib/i18n-extra";
import { hash, loadTicks, saveTicks } from "@/lib/recent";
import type { Analysis, Section } from "@/lib/types";
import type { Lang, T } from "@/lib/i18n";

type Kind = "fir" | "sp" | "magistrate";
type Tab = "overview" | "sections" | "steps" | "drafts" | "cases" | "summary";

const recommendedDraft = (a: Analysis): Kind | "" => {
  const s = a.answers.police_status;
  return s === "Yes, but police refused to register an FIR" ? "sp" : s === "Yes, FIR registered" ? "" : "fir";
};
const newOf = (s: Section, t: T) => s.bns.map((b) => b.provision).join(" / ") || t.no_counterpart;
const changeBadge = (s: { change?: string | null }, t: T) =>
  s.change === "Y" ? ["bg-amber-soft text-warn", t.text_changed] : s.change === "N" ? ["bg-ok/10 text-ok", t.same_law] : ["bg-mist text-slate", t.check_both];

function Card({ children, className = "", id }: { children: React.ReactNode; className?: string; id?: string }) {
  return <section id={id} className={`rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5 sm:p-6 ${className}`}>{children}</section>;
}

// ------------------------------------------------------------------ sidebar
function CaseCard({ a, t, onEditDetails }: { a: Analysis; t: T; onEditDetails: () => void }) {
  const r = a.regime;
  const decided = r.decision === "decided";
  const title = decided ? (r.law === "BNS" ? t.law_bns : t.law_ipc)
    : r.decision === "needs_review" ? t.law_review : r.decision === "abstain" ? t.law_abstain : t.law_unknown;
  const facts = Object.entries(a.answer_labels).filter(([k]) => k in t.inferred_labels);
  return (
    <section aria-labelledby="regime-h" className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-ink/5">
      <div className={`p-5 sm:p-6 ${decided ? "bg-ink text-white" : r.decision === "needs_review" ? "bg-amber-soft text-ink" : "bg-mist text-ink"}`}>
        <p className="text-xs font-semibold uppercase tracking-wider opacity-70">{t.which_law}</p>
        <h2 id="regime-h" className="mt-1 font-display text-2xl leading-snug">{title}</h2>
        {r.reason && <p className="mt-2 text-sm opacity-90">{r.reason}</p>}
        <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
          {(r.basis || []).map((b) => <span key={b} className="rounded-full bg-white/15 px-2.5 py-1 ring-1 ring-current/20">{b}</span>)}
          {a.procedure_code && <span className="rounded-full bg-white/15 px-2.5 py-1 ring-1 ring-current/20">{t.procedure}: {a.procedure_code}</span>}
        </div>
        <div className="mt-5"><Timeline t={t} date={a.answers.offence_date} dark={decided} /></div>
      </div>
      <div className="p-5 sm:p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">{t.facts_title}</h3>
          <button type="button" onClick={onEditDetails} className="rounded-md px-2 py-1 text-xs font-semibold text-sky hover:bg-mist print:hidden">{t.edit_details}</button>
        </div>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          {facts.map(([k, v]) => (
            <div key={k} className="min-w-0">
              <dt className="text-xs text-slate">{t.inferred_labels[k]}</dt>
              <dd className="truncate font-semibold text-ink" title={v}>{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function QuickActions({ a, t, narrative, answers, copySummary, copied }: {
  a: Analysis; t: T; narrative: string; answers: Record<string, string>; copySummary: () => void; copied: boolean;
}) {
  const rec = recommendedDraft(a);
  const [busy, setBusy] = useState(false);
  const label = rec === "sp" ? t.draft_sp : rec === "magistrate" ? t.draft_mag : t.draft_fir;
  const btn = "flex w-full items-center gap-3 rounded-xl border border-ink/10 px-3 py-2.5 text-left text-sm font-semibold text-ink transition hover:border-sky hover:bg-mist disabled:opacity-50";
  return (
    <Card className="print:hidden">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">{t.quick_actions}</h3>
      <div className="mt-3 space-y-2">
        {a.understood && rec && (
          <button type="button" className={`${btn} border-amber bg-amber-soft/60`} disabled={busy}
            onClick={async () => { setBusy(true); try { await downloadComplaint(narrative, answers, rec); } finally { setBusy(false); } }}>
            <span aria-hidden="true" className="text-lg">⬇</span><span>{busy ? t.downloading : `${label} (.docx)`}</span>
          </button>
        )}
        <button type="button" className={btn} onClick={() => window.print()}><span aria-hidden="true" className="text-lg">⎙</span>{t.print}</button>
        <button type="button" className={btn} onClick={copySummary}><span aria-hidden="true" className="text-lg">⧉</span>{copied ? t.copied : `${t.copy} — ${t.summary_title}`}</button>
      </div>
    </Card>
  );
}

function Helplines({ a, t }: { a: Analysis; t: T }) {
  const lines = [{ name: t.emergency.replace(/\s*112$/, ""), contact: "112" }, ...a.next_steps.helplines.filter((h) => !h.contact.startsWith("112"))];
  return (
    <Card>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">{t.helplines_title}</h3>
      <ul className="mt-3 space-y-2">
        {lines.map((h) => {
          const num = h.contact.match(/^\d+/)?.[0];
          return (
            <li key={h.name} className="flex items-center justify-between gap-3 rounded-xl bg-mist/70 px-3 py-2.5">
              <div className="min-w-0"><p className="font-bold text-ink">{h.contact}</p><p className="text-xs text-slate">{h.name}</p></div>
              {num && <a href={`tel:${num}`} className="shrink-0 rounded-lg bg-ink px-3 py-1.5 text-xs font-semibold text-white hover:bg-ink-2 print:hidden">{t.call}</a>}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

// ------------------------------------------------------------------ main panels
function SectionCard({ s, primary, t }: { s: Section; primary: Analysis["primary_code"]; t: T }) {
  const [open, setOpen] = useState(false);
  const [cls, label] = changeBadge(s, t);
  const box = (code: string, value: string, heading: string, applies: boolean, tone: string) => (
    <div className={`flex-1 rounded-xl p-4 ${applies ? `${tone} ring-2` : "bg-mist/60"}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate">{code}</span>
        {primary !== "both" && <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${applies ? "bg-ink text-white" : "bg-white text-slate"}`}>{applies ? t.applies_you : t.reference}</span>}
      </div>
      <p className="mt-1 font-mono text-xl font-bold text-ink">{value}</p>
      <p className="mt-0.5 text-sm text-ink-2">{heading}</p>
    </div>
  );
  return (
    <li className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-semibold text-ink">{s.offence}</p>
        <div className="flex flex-wrap gap-1.5 text-xs font-semibold">
          {s.status === "multiple_targets" && <span className="rounded-full bg-amber-soft px-2.5 py-1 text-warn">{t.split_badge}</span>}
          <span className={`rounded-full px-2.5 py-1 ${cls}`}>{label}</span>
        </div>
      </div>
      <div className="mt-3 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
        {box(`${t.old_label} · IPC`, `IPC ${s.ipc}`, s.ipc_heading, primary === "IPC", "bg-sky/10 ring-sky")}
        <span aria-hidden="true" className="self-center text-2xl text-amber sm:px-1">➜</span>
        {box(`${t.new_label} · BNS`, newOf(s, t), s.bns.map((b) => b.heading).filter(Boolean).join(" / ") || "", primary === "BNS", "bg-amber-soft ring-amber")}
      </div>
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="mt-3 text-sm font-medium text-ink-2 underline-offset-4 hover:underline print:hidden">
        {open ? `▾ ${t.hide_details}` : `▸ ${t.show_details}`}
      </button>
      <div className={`${open ? "" : "hidden"} mt-2 space-y-1 text-sm print:block`}>
        {s.mapping_explained && <p className="text-slate">{s.mapping_explained}</p>}
        {s.notes.length > 0 && <p className="text-ink"><span className="font-semibold">{t.what_changed} </span>{s.notes.join(" ")}</p>}
        <p className="text-xs text-slate">
          {s.basis === "offence rules" && s.evidence.length > 0 && <>{t.matched_from}: “{s.evidence[0]}” · </>}
          {t.source} {s.row_ids[0] && <>{t.row} {s.row_ids[0]}</>}{s.source?.page && <> · {t.page} {s.source.page}</>}
        </p>
      </div>
    </li>
  );
}

function Overview({ a, t, go, onEdit }: { a: Analysis; t: T; go: (tab: Tab) => void; onEdit: () => void }) {
  if (!a.understood) {
    return (
      <Card>
        <h2 className="font-display text-xl">{t.not_understood}</h2>
        <p className="mt-2 text-slate">{t.not_understood_help}</p>
        <button onClick={onEdit} className="mt-4 rounded-xl bg-ink px-5 py-2.5 font-semibold text-white">{t.edit_description}</button>
      </Card>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
      <Card className="xl:col-span-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">{t.overview_offences}</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {a.offences.map((o) => <span key={o.id} className="rounded-full bg-amber-soft px-3 py-1 text-sm font-semibold text-ink">{o.label}</span>)}
        </div>
        <div className="mt-6 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">{t.overview_sections}</h3>
          <button type="button" onClick={() => go("sections")} className="text-xs font-semibold text-sky hover:underline print:hidden">{t.see_all} →</button>
        </div>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-sm">
            <thead><tr className="border-b border-ink/10 text-xs text-slate">
              <th className="py-2 pr-3 font-semibold">{t.old_label}</th><th className="py-2 pr-3 font-semibold">{t.new_label}</th><th className="py-2 font-semibold"> </th>
            </tr></thead>
            <tbody>
              {a.sections.map((s) => {
                const [cls, label] = changeBadge(s, t);
                return (
                  <tr key={s.ipc} className="cursor-pointer border-b border-ink/5 last:border-0 hover:bg-mist/50" onClick={() => go("sections")}>
                    <td className={`whitespace-nowrap py-2.5 pr-3 font-mono font-bold ${a.primary_code === "IPC" ? "text-sky" : "text-ink/60"}`}>IPC {s.ipc}</td>
                    <td className={`whitespace-nowrap py-2.5 pr-3 font-mono font-bold ${a.primary_code === "BNS" ? "text-ink" : "text-ink/60"}`}>{newOf(s, t)}</td>
                    <td className="py-2.5"><span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls}`}>{label}</span>
                      <span className="ml-2 hidden text-xs text-slate md:inline">{s.ipc_heading}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {a.extra_laws.map((x) => (
          <p key={x.law} className="mt-4 rounded-xl bg-mist p-3 text-sm text-ink"><span className="font-semibold">{x.law}: </span>{x.sections}. <span className="text-slate">{x.note}</span></p>
        ))}
        {a.explanation && <p className="mt-4 rounded-xl bg-mist/60 p-4 text-ink">{a.explanation}</p>}
      </Card>
      <Card className="xl:col-span-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate">{t.overview_next}</h3>
          <button type="button" onClick={() => go("steps")} className="text-xs font-semibold text-sky hover:underline print:hidden">{t.see_all} →</button>
        </div>
        <ol className="mt-3 space-y-4">
          {a.next_steps.steps.slice(0, 3).map((st, i) => (
            <li key={st.title} className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber text-sm font-bold text-ink">{i + 1}</span>
              <div><p className="font-semibold text-ink">{st.title}</p><p className="line-clamp-3 text-sm text-slate">{st.detail}</p></div>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}

function Steps({ a, t, lang, narrative }: { a: Analysis; t: T; lang: Lang; narrative: string }) {
  const key = useMemo(() => hash(narrative.trim()), [narrative]);
  const [ticks, setTicks] = useState<Record<string, boolean>>({});
  useEffect(() => { setTicks(loadTicks(key)); }, [key]);
  const toggle = (id: string) => { const v = { ...ticks, [id]: !ticks[id] }; setTicks(v); saveTicks(key, v); };
  const groups = Array.from(new Set(a.offences.map((o) => EVIDENCE_GROUP_OF[o.id]).filter(Boolean))) as EvidenceGroup[];
  const evidence = [...EVIDENCE[lang].common.map((x, i) => [`c${i}`, x]), ...groups.flatMap((g) => EVIDENCE[lang][g].map((x, i) => [`${g}${i}`, x]))];
  const done = a.next_steps.steps.filter((_, i) => ticks[`s${i}`]).length;
  const total = a.next_steps.steps.length;
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
      <Card className="xl:col-span-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-2xl text-ink">{t.checklist_title}</h2>
          <span className="text-sm font-semibold text-ink-2">{t.checklist_done.replace("{n}", String(done)).replace("{m}", String(total))}</span>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-mist"><div className="h-full rounded-full bg-ok transition-all" style={{ width: `${total ? (done / total) * 100 : 0}%` }} /></div>
        <ol className="mt-5 space-y-3">
          {a.next_steps.steps.map((st, i) => {
            const on = !!ticks[`s${i}`];
            return (
              <li key={st.title}>
                <label className={`flex cursor-pointer gap-4 rounded-xl border p-4 transition ${on ? "border-ok/30 bg-ok/5" : "border-ink/10 hover:border-sky"}`}>
                  <input type="checkbox" checked={on} onChange={() => toggle(`s${i}`)} className="mt-1 h-5 w-5 shrink-0 accent-[#2e7d4f]" />
                  <div>
                    <p className={`font-semibold ${on ? "text-ok line-through decoration-2" : "text-ink"}`}><span className="mr-1 text-slate">{i + 1}.</span>{st.title}</p>
                    <p className="mt-0.5 text-sm text-slate">{st.detail}</p>
                  </div>
                </label>
              </li>
            );
          })}
        </ol>
      </Card>
      <Card className="xl:col-span-2">
        <h2 className="font-display text-xl text-ink">{t.evidence_title}</h2>
        <p className="mt-1 text-sm text-slate">{t.evidence_help}</p>
        <ul className="mt-4 space-y-2">
          {evidence.map(([id, x]) => (
            <li key={id}>
              <label className="flex cursor-pointer items-start gap-3 text-sm">
                <input type="checkbox" checked={!!ticks[`e${id}`]} onChange={() => toggle(`e${id}`)} className="mt-0.5 h-4 w-4 shrink-0 accent-[#2e7d4f]" />
                <span className={ticks[`e${id}`] ? "text-slate line-through" : "text-ink"}>{x}</span>
              </label>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function Drafts({ a, t, narrative, answers }: { a: Analysis; t: T; narrative: string; answers: Record<string, string> }) {
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const rec = recommendedDraft(a);
  const go = async (kind: Kind) => {
    setBusy(kind); setErr("");
    try { await downloadComplaint(narrative, answers, kind); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(""); }
  };
  const items: [Kind, string, string][] = [["fir", t.draft_fir, "1"], ["sp", t.draft_sp, "2"], ["magistrate", t.draft_mag, "3"]];
  return (
    <Card>
      <h2 className="font-display text-2xl text-ink">{t.draft_title}</h2>
      <p className="mt-1 max-w-3xl text-sm text-slate">{t.draft_help}</p>
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {items.map(([k, label, n]) => (
          <button key={k} type="button" disabled={!!busy} onClick={() => go(k)}
            className={`relative flex flex-col items-start rounded-2xl border p-5 text-left transition hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50 ${rec === k ? "border-amber bg-amber-soft/60" : "border-ink/10 hover:border-sky"}`}>
            {rec === k && <span className="absolute right-3 top-3 rounded-full bg-amber px-2 py-0.5 text-xs font-bold text-ink">{t.recommended}</span>}
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-ink font-bold text-white">{n}</span>
            <span className="mt-3 font-semibold text-ink">{label}</span>
            <span className="mt-auto pt-3 text-xs font-semibold text-sky">{busy === k ? t.downloading : "Word .docx ↓"}</span>
          </button>
        ))}
      </div>
      {err && <p role="alert" className="mt-3 text-sm text-warn">{err}</p>}
    </Card>
  );
}

// highlight the words the passage shares with the user's description (stems for words, digits for amounts)
function Highlight({ text, terms }: { text: string; terms: string[] }) {
  if (!terms.length) return <>{text}</>;
  const parts = terms.map((w) => /^\d/.test(w)
    ? w.replace(/,/g, "").split("").join(",?")
    : `${w.toLowerCase().replace(/(ings|ing|ed|es|s)$/, "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\w*`);
  const rx = new RegExp(`(\\b(?:${parts.join("|")})\\b)`, "gi");
  return <>{text.split(rx).map((p, i) => (i % 2 ? <mark key={i} className="rounded bg-amber/40 px-0.5 text-ink">{p}</mark> : p))}</>;
}

function Cases({ a, t }: { a: Analysis; t: T }) {
  const bnsOf: Record<string, string> = Object.fromEntries(a.sections.map((s) => [s.ipc, s.bns.map((b) => b.provision).join(" / ")]));
  const sc = a.similar_cases;
  return (
    <Card>
      <h2 className="font-display text-2xl text-ink">{t.cases_title}</h2>
      {!sc.available ? <p className="mt-2 text-slate">{t.cases_off}</p> : (
        <>
          <p className="mt-1 max-w-4xl text-sm text-slate">{t.cases_help}</p>
          <ul className="mt-5 grid gap-4 xl:grid-cols-2">
            {sc.results.map((c) => {
              const terms = c.matched_terms ?? [];
              const outcome = (c.plain?.outcome && c.plain.outcome.toLowerCase() !== "not stated" ? c.plain.outcome : null) ?? c.outcome_text ?? null;
              const relevance = c.plain?.relevance && c.plain.relevance.toLowerCase() !== "unclear" ? c.plain.relevance : null;
              return (
                <li key={c.id} className="flex flex-col rounded-xl border border-ink/10 p-4">
                  {c.plain?.summary && (
                    <div className="mb-3 rounded-lg bg-mist/70 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate">{t.plain_label}</p>
                      <p className="mt-1 font-medium text-ink">{c.plain.summary}</p>
                    </div>
                  )}
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate">{t.court_words}</p>
                  <blockquote className="mt-1 border-l-2 border-ink/15 pl-3 text-sm leading-relaxed text-ink-2">
                    <Highlight text={c.snippet} terms={terms} />
                  </blockquote>
                  <p className={`mt-3 rounded-lg px-3 py-2 text-sm ${outcome ? "bg-ok/10" : "bg-mist/60"}`}>
                    <span className="font-semibold text-ink">{t.outcome_label}: </span>
                    <span className={outcome ? "text-ink" : "text-slate"}>{outcome ?? t.outcome_not_stated}</span>
                  </p>
                  <div className="mt-3 rounded-lg border border-dashed border-ink/15 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate">{t.why_matched}</p>
                    {relevance && <p className="mt-1 text-sm text-ink">{relevance}</p>}
                    {c.shared_sections.length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <span className="text-xs text-slate">{t.same_sections}:</span>
                        {c.shared_sections.map((sec) => (
                          <span key={sec} className="rounded-full bg-amber-soft px-2.5 py-0.5 text-xs font-semibold text-ink">IPC {sec}{bnsOf[sec] ? ` → ${bnsOf[sec]}` : ""}</span>
                        ))}
                      </div>
                    )}
                    {terms.length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <span className="text-xs text-slate">{t.shared_words}:</span>
                        {terms.map((w) => <mark key={w} className="rounded bg-amber/40 px-1.5 text-xs font-semibold text-ink">{w}</mark>)}
                      </div>
                    )}
                  </div>
                  <p className="mt-auto pt-3 text-xs text-slate">{t.all_sections} IPC {c.ipc.join(", ")} · {c.source}</p>
                </li>
              );
            })}
          </ul>
          {sc.plain_by && <p className="mt-4 text-xs text-slate">ⓘ {t.ai_note.replace("{m}", sc.plain_by)}</p>}
        </>
      )}
    </Card>
  );
}

function Summary({ a, t, copy, copied }: { a: Analysis; t: T; copy: () => void; copied: boolean }) {
  const download = () => {
    const url = URL.createObjectURL(new Blob([a.summary], { type: "text/plain;charset=utf-8" }));
    const el = document.createElement("a");
    el.href = url; el.download = "legalcompass-case-summary.txt"; el.click(); URL.revokeObjectURL(url);
  };
  const canShare = typeof navigator !== "undefined" && "share" in navigator;
  const share = async () => { try { await navigator.share({ title: "LegalCompass case summary", text: a.summary }); } catch { /* cancelled */ } };
  const wa = `https://wa.me/?text=${encodeURIComponent(a.summary.slice(0, 3500))}`;
  const mail = `mailto:?subject=${encodeURIComponent("Case summary (LegalCompass)")}&body=${encodeURIComponent(a.summary.slice(0, 1800))}`;
  const b = "rounded-lg border border-ink/20 px-4 py-2 text-sm font-semibold text-ink hover:bg-mist";
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl text-ink">{t.summary_title}</h2>
        <div className="flex flex-wrap gap-2 print:hidden">
          <button onClick={copy} className={b}>{copied ? t.copied : t.copy}</button>
          <button onClick={download} className={b}>{t.download}</button>
          {canShare && <button onClick={share} className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-ink-2">{t.share}</button>}
          <a href={wa} target="_blank" rel="noopener noreferrer" className={b}>{t.share_whatsapp}</a>
          <a href={mail} className={b}>{t.share_email}</a>
        </div>
      </div>
      <p className="mt-1 text-sm text-slate">{t.summary_help}</p>
      <pre className="mt-4 max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-xl bg-mist/60 p-5 font-mono text-[13px] leading-relaxed text-ink print:max-h-none">{a.summary}</pre>
    </Card>
  );
}

// ------------------------------------------------------------------ page
export default function Results({ t, lang, a, narrative, answers, onRestart, onEdit, onEditDetails }: {
  t: T; lang: Lang; a: Analysis; narrative: string; answers: Record<string, string>;
  onRestart: () => void; onEdit: () => void; onEditDetails: () => void;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(a.summary); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* blocked */ }
  };
  const tabs: [Tab, string, number | null][] = [
    ["overview", t.tab_overview, null],
    ["sections", t.tab_sections, a.sections.length],
    ["steps", t.tab_steps, a.next_steps.steps.length],
    ...(a.understood ? [["drafts", t.tab_drafts, 3] as [Tab, string, number]] : []),
    ["cases", t.tab_cases, a.similar_cases.available ? a.similar_cases.results.length : null],
    ["summary", t.tab_summary, null],
  ];
  const go = (x: Tab) => { setTab(x); document.getElementById("results-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" }); };
  const panel = (id: Tab, node: React.ReactNode) => (
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} className={`${tab === id ? "" : "hidden"} print:mb-6 print:block`}>{node}</div>
  );

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <aside className="space-y-4 lg:col-span-4 xl:col-span-3">
        <div className="space-y-4 lg:sticky lg:top-24">
          <CaseCard a={a} t={t} onEditDetails={onEditDetails} />
          <div className="hidden space-y-4 lg:block">
            <QuickActions a={a} t={t} narrative={narrative} answers={answers} copySummary={copy} copied={copied} />
            <Helplines a={a} t={t} />
          </div>
        </div>
      </aside>

      <div className="min-w-0 lg:col-span-8 xl:col-span-9">
        <div id="results-tabs" className="sticky top-[113px] z-10 md:top-16 -mx-1 mb-5 scroll-mt-24 overflow-x-auto bg-[#f6f8fc]/95 px-1 py-2 backdrop-blur print:hidden">
          <div role="tablist" aria-label={t.step_results} className="inline-flex min-w-full gap-1 rounded-2xl bg-white p-1.5 shadow-sm ring-1 ring-ink/5">
            {tabs.map(([id, label, n]) => (
              <button key={id} id={`tab-${id}`} role="tab" type="button" aria-selected={tab === id} aria-controls={`panel-${id}`} onClick={() => setTab(id)}
                className={`flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold transition ${tab === id ? "bg-ink text-white shadow" : "text-ink-2 hover:bg-mist"}`}>
                {label}
                {n !== null && <span className={`rounded-full px-1.5 text-xs ${tab === id ? "bg-amber text-ink" : "bg-mist text-slate"}`}>{n}</span>}
              </button>
            ))}
          </div>
        </div>

        {panel("overview", <Overview a={a} t={t} go={go} onEdit={onEdit} />)}
        {panel("sections", (
          <div>
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h2 className="font-display text-2xl text-ink">{t.sections_title}</h2>
              <span className="text-sm text-slate">{t.sections_sub}</span>
            </div>
            <ul className="grid gap-4 2xl:grid-cols-2">{a.sections.map((s) => <SectionCard key={s.ipc} s={s} primary={a.primary_code} t={t} />)}</ul>
            {a.lang !== "en" && <p className="mt-3 text-xs text-slate">{t.english_note}</p>}
          </div>
        ))}
        {panel("steps", <Steps a={a} t={t} lang={lang} narrative={narrative} />)}
        {a.understood && panel("drafts", <Drafts a={a} t={t} narrative={narrative} answers={answers} />)}
        {panel("cases", <Cases a={a} t={t} />)}
        {panel("summary", <Summary a={a} t={t} copy={copy} copied={copied} />)}

        {/* on phones the actions and helplines come after the results */}
        <div className="mt-6 space-y-4 lg:hidden print:hidden">
          <QuickActions a={a} t={t} narrative={narrative} answers={answers} copySummary={copy} copied={copied} />
          <Helplines a={a} t={t} />
        </div>

        <div className="mt-8 flex flex-wrap justify-between gap-3 print:hidden">
          <button onClick={onEdit} className="text-sm font-medium text-ink-2 underline-offset-4 hover:underline">{t.edit_description}</button>
          <button onClick={onRestart} className="rounded-xl border border-ink/20 bg-white px-5 py-2.5 font-semibold text-ink hover:bg-mist">{t.start_new}</button>
        </div>
      </div>
    </div>
  );
}
