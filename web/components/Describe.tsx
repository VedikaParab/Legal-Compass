"use client";

import { useState } from "react";
import DocumentUpload from "./DocumentUpload";
import { EXAMPLE_TEXTS, type Lang, type T } from "@/lib/i18n";

const ICONS = [
  // phone (online fraud), hand (assault), home with heart (dowry), lock (burglary)
  "M7 2h10a1 1 0 011 1v18a1 1 0 01-1 1H7a1 1 0 01-1-1V3a1 1 0 011-1zm4 17h2",
  "M8 13V5a1.5 1.5 0 013 0v6m0-1V4a1.5 1.5 0 013 0v6m0-1V6a1.5 1.5 0 013 0v8a7 7 0 01-7 7h-1a6 6 0 01-5-3l-2.5-4a1.5 1.5 0 012.5-1.6L8 13",
  "M3 11l9-7 9 7v9a1 1 0 01-1 1H4a1 1 0 01-1-1v-9zm9 7s-3.5-2-3.5-4.2a1.8 1.8 0 013.5-.6 1.8 1.8 0 013.5.6C15.5 16 12 18 12 18z",
  "M6 11V8a6 6 0 1112 0v3M5 11h14v10H5V11zm7 4v2",
];

// light-weight hints so people know what to include (multi-script, deliberately loose)
const TIPS: [keyof T, RegExp][] = [
  ["tip_when", /\b(19|20)\d{2}\b|[०-९]{4}|today|yesterday|ago|last (week|month|night)|आज|कल|पिछले|गेल्या|काल/i],
  ["tip_where", /\b(in|at|near|outside|from)\s+(my\s+)?[A-Za-z]{3,}|में|मध्ये|जवळ|पास|त\s|बाहेर/],
  ["tip_what", /(\S+\s+){7,}/],
  ["tip_loss", /rs\.?\s?\d|₹|rupee|lakh|stole|took|snatch|hurt|injur|fractur|hospital|beat|hit|रुपये|रुपए|चोट|इजा|चोरी|गहने|दागिने|मार|हड्डी|हाड/i],
  ["tip_police", /police|\bfir\b|station|complaint|पुलिस|थान|एफआईआर|पोलीस|एफआयआर|ठाण|तक्रार|शिकायत/i],
];

export default function Describe({ t, lang, initial, busy, onSubmit }: {
  t: T; lang: Lang; initial: string; busy: boolean; onSubmit: (text: string) => void;
}) {
  const [text, setText] = useState(initial);
  const [tab, setTab] = useState<"type" | "upload">("type");
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  const tooShort = words < 5;

  return (
    <section aria-labelledby="describe-h" className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="describe-h" className="font-display text-2xl text-ink sm:text-3xl">{t.what_happened}</h2>
        <div role="tablist" aria-label={t.what_happened} className="inline-flex rounded-xl bg-mist p-1">
          {(["type", "upload"] as const).map((id) => (
            <button key={id} role="tab" type="button" aria-selected={tab === id} onClick={() => setTab(id)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${tab === id ? "bg-white text-ink shadow-sm" : "text-ink-2 hover:text-ink"}`}>
              {id === "type" ? t.tab_type : t.tab_upload}
            </button>
          ))}
        </div>
      </div>

      {tab === "upload" ? (
        <DocumentUpload t={t} lang={lang} onUse={(doc) => { setText(doc); setTab("type"); onSubmit(doc); }} />
      ) : (
        <>
          <p className="mt-3 max-w-3xl text-slate">{t.describe_help}</p>

          <p className="mt-5 text-sm font-semibold text-ink">{t.try_example}</p>
          <div className="mt-2 grid grid-cols-2 gap-2 lg:grid-cols-4">
            {EXAMPLE_TEXTS[lang].map((ex, i) => (
              <button key={i} type="button" onClick={() => setText(ex)}
                className={`group flex items-center gap-3 rounded-xl border p-3 text-left transition hover:-translate-y-0.5 hover:border-sky hover:shadow-sm ${text === ex ? "border-sky bg-mist" : "border-ink/10"}`}>
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-soft text-ink group-hover:bg-amber">
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={ICONS[i]} /></svg>
                </span>
                <span className="text-sm font-semibold text-ink">{t.examples[i]}</span>
              </button>
            ))}
          </div>

          <label htmlFor="narrative" className="sr-only">{t.what_happened}</label>
          <textarea id="narrative" value={text} onChange={(e) => setText(e.target.value)} rows={8} placeholder={t.placeholder}
            className="mt-4 w-full resize-y rounded-xl border border-ink/15 bg-mist/30 p-4 text-base leading-relaxed text-ink placeholder:text-slate/70 focus:border-sky focus:bg-white focus:outline-none" />

          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate">{t.tips_title}</span>
            {TIPS.map(([k, re]) => {
              const ok = re.test(text);
              return (
                <span key={k} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold transition ${ok ? "bg-ok/10 text-ok" : "bg-mist text-slate"}`}>
                  <span aria-hidden="true">{ok ? "✓" : "○"}</span>{t[k] as string}
                </span>
              );
            })}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
            <p className="text-xs text-slate">{t.coming_soon}</p>
            <button type="button" disabled={busy || tooShort} onClick={() => onSubmit(text)}
              className="rounded-xl bg-ink px-7 py-3 font-semibold text-white shadow-sm transition hover:bg-ink-2 disabled:cursor-not-allowed disabled:opacity-40">
              {busy ? t.reading : `${t.continue} →`}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
