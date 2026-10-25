"use client";

import { useState } from "react";
import Timeline from "./Timeline";
import type { Analysis, Question } from "@/lib/types";
import type { T } from "@/lib/i18n";

function Field({ q, value, onChange }: { q: Question; value: string; onChange: (v: string) => void }) {
  if (q.kind === "choice") {
    return (
      <div className="flex flex-wrap gap-2">
        {q.options.map((opt, j) => {
          const on = value === opt;
          return (
            <button key={opt} type="button" aria-pressed={on} onClick={() => onChange(on ? "" : opt)}
              className={`rounded-lg border px-3 py-2 text-sm transition ${on ? "border-ink bg-ink text-white" : "border-ink/15 bg-white text-ink hover:border-sky hover:bg-mist"}`}>
              {q.option_labels?.[j] ?? opt}
            </button>
          );
        })}
      </div>
    );
  }
  if (q.kind === "date") {
    return <input type="date" aria-label={q.text} value={value} max={new Date().toISOString().slice(0, 10)} onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-ink focus:border-sky focus:outline-none" />;
  }
  return <input type="text" aria-label={q.text} value={value} onChange={(e) => onChange(e.target.value)}
    className="w-full max-w-sm rounded-lg border border-ink/15 bg-white px-3 py-2 text-ink focus:border-sky focus:outline-none" />;
}

export default function Questions({ t, analysis, busy, initial, onSubmit, onRefresh, onBack }: {
  t: T;
  analysis: Analysis;
  busy: boolean;
  initial: Record<string, string>;
  onSubmit: (answers: Record<string, string>, finalize: boolean) => void;
  onRefresh: (facts: Record<string, string>) => void;
  onBack: () => void;
}) {
  const [vals, setVals] = useState<Record<string, string>>(initial);
  const [editing, setEditing] = useState<string | null>(null);
  const qs = analysis.questions;
  const missingRequired = qs.filter((q) => q.required && !vals[q.id]);
  const facts = analysis.inferred_questions ?? [];
  const factIds = new Set(facts.map((f) => f.id));
  const answered = qs.filter((q) => vals[q.id]).length;
  const valueOf = (id: string) => vals[id] ?? analysis.answers[id] ?? "";
  const labelOf = (q: Question) => {
    const v = valueOf(q.id);
    const j = q.options.indexOf(v);
    return j >= 0 ? (q.option_labels?.[j] ?? v) : (analysis.answer_labels[q.id] && v === analysis.answers[q.id] ? analysis.answer_labels[q.id] : v);
  };
  const finishEdit = () => {
    setEditing(null);
    // re-check with the corrected facts: a changed date can add or remove questions
    onRefresh(Object.fromEntries(Object.entries(vals).filter(([k, v]) => factIds.has(k) && v)));
  };
  const date = valueOf("offence_date");

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <section aria-labelledby="q-h" className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5 sm:p-8 lg:col-span-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="q-h" className="font-display text-2xl text-ink sm:text-3xl">{t.questions_title}</h2>
            <p className="mt-1 max-w-2xl text-slate">{t.questions_help}</p>
          </div>
          {qs.length > 0 && <p className="text-sm font-semibold text-ink-2">{answered} / {qs.length}</p>}
        </div>

        {qs.length === 0 && <p className="mt-6 rounded-xl bg-ok/10 p-4 font-medium text-ok">✓ {t.all_set}</p>}

        <ol className="mt-6 grid gap-4 xl:grid-cols-2">
          {qs.map((q, i) => (
            <li key={q.id} className={`rounded-xl border p-4 transition ${vals[q.id] ? "border-ok/40 bg-ok/5" : "border-ink/10"} ${q.kind === "choice" && q.options.length > 3 ? "xl:col-span-2" : ""}`}>
              <fieldset>
                <legend className="font-semibold text-ink">
                  <span className={`mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs text-white ${vals[q.id] ? "bg-ok" : "bg-ink"}`}>{vals[q.id] ? "✓" : i + 1}</span>
                  {q.text} {q.required && <span className="text-sm font-normal text-warn">{t.needed}</span>}
                </legend>
                <p className="mt-1 text-sm text-slate">{q.why}</p>
                <div className="mt-3"><Field q={q} value={vals[q.id] || ""} onChange={(v) => setVals({ ...vals, [q.id]: v })} /></div>
              </fieldset>
            </li>
          ))}
        </ol>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
          <button type="button" onClick={onBack} className="text-sm font-medium text-ink-2 underline-offset-4 hover:underline">{t.edit_description}</button>
          <div className="flex flex-wrap gap-3">
            {qs.length > 0 && <button type="button" disabled={busy} onClick={() => onSubmit(vals, true)}
              className="rounded-xl border border-ink/20 px-5 py-3 font-semibold text-ink hover:bg-mist disabled:opacity-40">{t.skip}</button>}
            <button type="button" disabled={busy || missingRequired.length > 0} onClick={() => onSubmit(vals, true)}
              className="rounded-xl bg-ink px-7 py-3 font-semibold text-white hover:bg-ink-2 disabled:cursor-not-allowed disabled:opacity-40">
              {busy ? t.analysing : `${t.see_results} →`}
            </button>
          </div>
        </div>
      </section>

      <aside className="space-y-4 lg:col-span-4">
        <section aria-labelledby="und-h" className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5 lg:sticky lg:top-24">
          <h2 id="und-h" className="font-display text-xl text-ink">{t.understood_title}</h2>
          {analysis.offences.length > 0 && (
            <>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-slate">{t.offences_found}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {analysis.offences.map((o) => <span key={o.id} className="rounded-full bg-amber-soft px-3 py-1 text-sm font-medium text-ink">{o.label}</span>)}
              </div>
            </>
          )}
          {facts.length > 0 && (
            <>
              <p className="mt-4 text-xs text-slate">{t.understood_help}</p>
              <dl className="mt-2 divide-y divide-ink/5">
                {facts.map((f) => (
                  <div key={f.id} className="py-2.5">
                    <div className="flex items-center justify-between gap-3">
                      <dt className="text-sm text-slate">{t.inferred_labels[f.id] ?? f.text}</dt>
                      {editing !== f.id && (
                        <dd className="flex items-center gap-2 text-right">
                          <span className="font-semibold text-ink">{labelOf(f) || t.nothing_yet}</span>
                          <button type="button" onClick={() => setEditing(f.id)} className="rounded-md px-2 py-0.5 text-xs font-semibold text-sky hover:bg-mist">{t.change}</button>
                        </dd>
                      )}
                    </div>
                    {editing === f.id && (
                      <div className="mt-2 rounded-lg bg-mist/60 p-3">
                        <Field q={f} value={valueOf(f.id)} onChange={(v) => setVals({ ...vals, [f.id]: v })} />
                        <button type="button" onClick={finishEdit} disabled={busy} className="mt-2 rounded-md bg-ink px-3 py-1.5 text-xs font-semibold text-white">
                          {busy ? t.updating : t.done}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </dl>
            </>
          )}
          <div className="mt-4 border-t border-ink/5 pt-4"><Timeline t={t} date={date || null} /></div>
        </section>
      </aside>
    </div>
  );
}
