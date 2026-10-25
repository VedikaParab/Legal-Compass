"use client";

import { useEffect, useState } from "react";
import Describe from "@/components/Describe";
import Questions from "@/components/Questions";
import Results from "@/components/Results";
import { Converter, DateChecker, Glossary } from "@/components/Tools";
import { analyze, ping } from "@/lib/api";
import { DICTS, LANGS, type Lang, type T } from "@/lib/i18n";
import { clearRecent, loadRecent, saveRecent, type Recent } from "@/lib/recent";
import type { Analysis } from "@/lib/types";

type Step = "describe" | "questions" | "results";
type Tool = "converter" | "date" | "glossary";
const WRAP = "mx-auto w-full max-w-[1600px] px-4 sm:px-6 lg:px-10";

function Logo() {
  return (
    <svg aria-hidden="true" viewBox="0 0 40 40" className="h-9 w-9 shrink-0">
      <circle cx="20" cy="20" r="18" fill="#14213d" />
      <circle cx="20" cy="20" r="13" fill="none" stroke="#9aabc7" strokeWidth="1" />
      <path d="M20 6 L24 20 L20 34 L16 20 Z" fill="#f2a93b" />
    </svg>
  );
}

function Drawer({ tool, t, lang, onClose, onTool }: { tool: Tool; t: T; lang: Lang; onClose: () => void; onTool: (x: Tool) => void }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  const tabs: [Tool, string][] = [["converter", t.nav_converter], ["date", t.nav_date], ["glossary", t.nav_help]];
  return (
    <div className="fixed inset-0 z-50 print:hidden" role="dialog" aria-modal="true" aria-label={t.tools_title}>
      <button type="button" aria-label={t.close} onClick={onClose} className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" />
      <div className="absolute inset-y-0 right-0 flex w-full max-w-xl flex-col bg-[#f6f8fc] shadow-2xl">
        <div className="flex items-center justify-between border-b border-ink/10 bg-white px-5 py-4">
          <div role="tablist" className="flex gap-1 overflow-x-auto">
            {tabs.map(([id, label]) => (
              <button key={id} role="tab" type="button" aria-selected={tool === id} onClick={() => onTool(id)}
                className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-semibold ${tool === id ? "bg-ink text-white" : "text-ink-2 hover:bg-mist"}`}>{label}</button>
            ))}
          </div>
          <button type="button" onClick={onClose} aria-label={t.close} className="ml-3 rounded-lg p-2 text-xl leading-none text-slate hover:bg-mist">×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          {tool === "converter" && <><p className="mb-4 text-sm text-slate">{t.conv_help}</p><Converter t={t} lang={lang} autoFocus /></>}
          {tool === "date" && <div className="rounded-2xl bg-white p-5 ring-1 ring-ink/5"><DateChecker t={t} lang={lang} /></div>}
          {tool === "glossary" && <Glossary lang={lang} columns="grid-cols-1" />}
        </div>
      </div>
    </div>
  );
}

function RecentCases({ t, items, onOpen, onClear }: { t: T; items: Recent[]; onOpen: (r: Recent) => void; onClear: () => void }) {
  return (
    <section aria-labelledby="recent-h" className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5">
      <div className="flex items-center justify-between">
        <h2 id="recent-h" className="font-display text-xl text-ink">{t.recent_title}</h2>
        {items.length > 0 && <button type="button" onClick={onClear} className="text-xs font-semibold text-slate hover:text-warn">{t.recent_clear}</button>}
      </div>
      <p className="text-xs text-slate">{t.recent_help}</p>
      {items.length === 0 ? <p className="mt-3 rounded-xl bg-mist/60 p-3 text-sm text-slate">{t.recent_empty}</p> : (
        <ul className="mt-3 space-y-2">
          {items.map((r) => (
            <li key={r.id}>
              <button type="button" onClick={() => onOpen(r)} className="group w-full rounded-xl border border-ink/10 p-3 text-left transition hover:border-sky hover:bg-mist/50">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-ink">{r.title}</span>
                  {r.law && <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${r.law === "BNS" ? "bg-amber text-ink" : "bg-sky text-white"}`}>{r.law}</span>}
                </div>
                <p className="mt-0.5 truncate text-xs text-slate">{r.sections.join(" · ") || r.narrative.slice(0, 70)}</p>
                <p className="mt-1 text-[11px] text-slate/80">{new Date(r.at).toLocaleDateString()} · <span className="text-sky group-hover:underline">{t.recent_open} →</span></p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function Home() {
  const [lang, setLang] = useState<Lang>("en");
  const [step, setStep] = useState<Step>("describe");
  const [narrative, setNarrative] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [prefill, setPrefill] = useState<Record<string, string>>({});
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [waking, setWaking] = useState(false);
  const [tool, setTool] = useState<Tool | null>(null);
  const [recent, setRecent] = useState<Recent[]>([]);
  const t = DICTS[lang];

  // Free hosting puts the backend to sleep when idle: wake it as soon as the page opens and say so if it is slow.
  useEffect(() => {
    let done = false;
    const slow = setTimeout(() => { if (!done) setWaking(true); }, 2500);
    ping().finally(() => { done = true; clearTimeout(slow); setWaking(false); });
    return () => clearTimeout(slow);
  }, []);

  useEffect(() => {
    try { const s = localStorage.getItem("lc-lang") as Lang | null; if (s && s in DICTS) setLang(s); } catch { /* storage blocked */ }
    setRecent(loadRecent());
  }, []);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const run = async (text: string, ans: Record<string, string>, finalize: boolean, l: Lang = lang, stay = false) => {
    setBusy(true); setError("");
    try {
      const a = await analyze(text, ans, finalize, l);
      setAnalysis(a); setAnswers(ans);
      const next: Step = stay ? "questions" : !finalize && a.questions.length > 0 ? "questions" : "results";
      if (next === "results") setRecent(saveRecent(a, text, ans));
      if (next !== step) window.scrollTo({ top: 0, behavior: "smooth" });
      setStep(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const changeLang = (l: Lang) => {
    setLang(l);
    try { localStorage.setItem("lc-lang", l); } catch { /* storage blocked */ }
    if (analysis && narrative && step !== "describe") run(narrative, answers, step === "results", l, step === "questions");
  };

  // back to the questions with everything answered so far; corrected facts are kept so the questions match them
  const editDetails = () => {
    const facts = new Set((analysis?.inferred_questions ?? []).map((q) => q.id));
    setPrefill(answers);
    run(narrative, Object.fromEntries(Object.entries(answers).filter(([k]) => facts.has(k))), false, lang, true);
  };
  const restart = () => { setNarrative(""); setAnswers({}); setPrefill({}); setAnalysis(null); setStep("describe"); window.scrollTo({ top: 0 }); };
  const steps: [Step, string][] = [["describe", t.step_describe], ["questions", t.step_details], ["results", t.step_results]];
  const idx = steps.findIndex(([s]) => s === step);
  const navBtn = "whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold text-ink-2 hover:bg-mist hover:text-ink";

  return (
    <div className="flex min-h-screen flex-col">
      {/* ------------------------------------------------ top bar */}
      <header className="sticky top-0 z-40 border-b border-ink/10 bg-white/90 backdrop-blur print:static">
        <div className={`${WRAP} flex h-16 items-center gap-3`}>
          <button type="button" onClick={restart} className="flex items-center gap-2.5" aria-label="LegalCompass — home">
            <Logo />
            <span className="font-display text-xl text-ink sm:text-2xl">LegalCompass</span>
          </button>
          <nav aria-label="Tools" className="ml-4 hidden items-center gap-1 md:flex print:hidden">
            <button type="button" onClick={restart} className={`${navBtn} ${step === "describe" ? "bg-mist text-ink" : ""}`}>{t.nav_case}</button>
            <button type="button" onClick={() => setTool("converter")} className={navBtn}>{t.nav_converter}</button>
            <button type="button" onClick={() => setTool("date")} className={navBtn}>{t.nav_date}</button>
            <button type="button" onClick={() => setTool("glossary")} className={navBtn}>{t.nav_help}</button>
          </nav>
          <div className="ml-auto flex items-center gap-2 print:hidden">
            <div role="group" aria-label="Language" className="inline-flex rounded-lg bg-mist p-0.5">
              {LANGS.map((l) => (
                <button key={l.id} type="button" aria-pressed={lang === l.id} onClick={() => changeLang(l.id)}
                  className={`rounded-md px-2.5 py-1.5 text-xs font-semibold sm:px-3 sm:text-sm ${lang === l.id ? "bg-ink text-white" : "text-ink-2 hover:bg-white"}`}>
                  {l.label}
                </button>
              ))}
            </div>
            <a href="tel:112" className="hidden items-center gap-1.5 rounded-lg bg-[#c0392b] px-3 py-2 text-sm font-bold text-white hover:bg-[#a93226] sm:inline-flex">
              <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-white" />{t.emergency}
            </a>
          </div>
        </div>
        {/* tools on small screens */}
        <nav aria-label="Tools" className="flex gap-1 overflow-x-auto border-t border-ink/5 px-3 py-1.5 md:hidden print:hidden">
          <button type="button" onClick={() => setTool("converter")} className={navBtn}>{t.nav_converter}</button>
          <button type="button" onClick={() => setTool("date")} className={navBtn}>{t.nav_date}</button>
          <button type="button" onClick={() => setTool("glossary")} className={navBtn}>{t.nav_help}</button>
          <a href="tel:112" className="whitespace-nowrap rounded-lg bg-[#c0392b] px-3 py-2 text-sm font-bold text-white">{t.emergency}</a>
        </nav>
      </header>

      {/* ------------------------------------------------ hero (first screen only) */}
      {step === "describe" && (
        <section className="relative overflow-hidden bg-ink text-white">
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[0.07]"
            style={{ backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)", backgroundSize: "22px 22px" }} />
          <div aria-hidden="true" className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-amber/20 blur-3xl" />
          <div className={`${WRAP} relative grid grid-cols-1 gap-10 py-10 lg:grid-cols-12 lg:py-14`}>
            <div className="lg:col-span-7">
              <p className="inline-flex rounded-full bg-white/10 px-3 py-1 text-xs font-semibold tracking-wide text-amber ring-1 ring-white/15">{t.hero_kicker}</p>
              <h1 className="mt-4 max-w-3xl font-display text-3xl leading-tight sm:text-4xl xl:text-5xl">{t.hero_title}</h1>
              <p className="mt-4 max-w-2xl text-base leading-relaxed text-white/80 sm:text-lg">{t.hero_sub}</p>
              <ol className="mt-8 grid gap-3 sm:grid-cols-3">
                {([[t.how_1_t, t.how_1], [t.how_2_t, t.how_2], [t.how_3_t, t.how_3]] as const).map(([h, d], i) => (
                  <li key={h} className="flex gap-3 rounded-xl bg-white/5 p-4 ring-1 ring-white/10">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber font-bold text-ink">{i + 1}</span>
                    <div><p className="font-semibold">{h}</p><p className="text-sm text-white/70">{d}</p></div>
                  </li>
                ))}
              </ol>
            </div>
            <div className="lg:col-span-5">
              <div className="rounded-2xl bg-white/[0.06] p-5 ring-1 ring-white/15 sm:p-6">
                <p className="text-xs font-semibold uppercase tracking-wider text-amber">{t.tl_title}</p>
                <div className="mt-3"><DateChecker t={t} lang={lang} dark /></div>
              </div>
            </div>
          </div>
        </section>
      )}

      <main className={`${WRAP} flex-1 pb-16 ${step === "describe" ? "pt-8" : "pt-6"}`}>
        {step !== "describe" && (
          <nav aria-label="Progress" className="mb-6 print:hidden">
            <ol className="flex items-center gap-2 sm:gap-4">
              {steps.map(([id, label], i) => {
                const state = i < idx ? "done" : i === idx ? "now" : "todo";
                return (
                  <li key={id} className="flex flex-1 items-center gap-2 sm:gap-3">
                    <button type="button" disabled={state === "todo" || busy} aria-current={state === "now" ? "step" : undefined}
                      onClick={() => (id === "describe" ? setStep("describe") : id === "questions" && state === "done" ? editDetails() : undefined)}
                      className="flex items-center gap-2 disabled:cursor-default">
                      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${state === "todo" ? "bg-ink/10 text-slate" : state === "now" ? "bg-amber text-ink" : "bg-ink text-white"}`}>
                        {state === "done" ? "✓" : i + 1}
                      </span>
                      <span className={`hidden text-sm font-semibold sm:inline ${state === "todo" ? "text-slate/70" : "text-ink"}`}>{label}</span>
                    </button>
                    {i < steps.length - 1 && <span className={`h-0.5 flex-1 rounded ${i < idx ? "bg-ink" : "bg-ink/10"}`} />}
                  </li>
                );
              })}
            </ol>
          </nav>
        )}

        {waking && <div role="status" className="mb-4 flex items-center gap-3 rounded-xl bg-mist p-4 text-sm text-ink">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-ink/20 border-t-ink" aria-hidden="true" />{t.waking}</div>}
        {error && <div role="alert" className="mb-4 rounded-xl bg-amber-soft p-4 text-sm text-warn">{error}</div>}

        {step === "describe" && (
          <>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="lg:col-span-8">
                <Describe key={lang} t={t} lang={lang} initial={narrative} busy={busy}
                  onSubmit={(text) => { setNarrative(text); setPrefill({}); run(text, {}, false); }} />
              </div>
              <aside className="space-y-6 lg:col-span-4">
                <section aria-labelledby="conv-h" className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-ink/5">
                  <h2 id="conv-h" className="font-display text-xl text-ink">{t.conv_title}</h2>
                  <p className="mb-3 text-xs text-slate">{t.conv_help}</p>
                  <Converter t={t} lang={lang} />
                </section>
                <RecentCases t={t} items={recent} onClear={() => { clearRecent(); setRecent([]); }}
                  onOpen={(r) => { setNarrative(r.narrative); setPrefill(r.answers); run(r.narrative, r.answers, true); }} />
                <section className="flex gap-3 rounded-2xl bg-ok/5 p-5 ring-1 ring-ok/15">
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6 shrink-0 text-ok" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z" /><path d="M9 12l2 2 4-4" /></svg>
                  <div><h2 className="font-semibold text-ink">{t.privacy_title}</h2><p className="mt-1 text-sm text-slate">{t.privacy_text}</p></div>
                </section>
              </aside>
            </div>
            <section aria-labelledby="gl-h" className="mt-12">
              <h2 id="gl-h" className="font-display text-2xl text-ink">{t.glossary_title}</h2>
              <div className="mt-4"><Glossary lang={lang} /></div>
            </section>
          </>
        )}
        {step === "questions" && analysis && (
          <Questions key={lang} t={t} analysis={analysis} busy={busy} initial={prefill} onBack={() => setStep("describe")}
            onRefresh={(facts) => run(narrative, facts, false, lang, true)}
            onSubmit={(ans, fin) => run(narrative, { ...analysis.answers, ...ans }, fin)} />
        )}
        {step === "results" && analysis && (
          <Results t={t} lang={lang} a={analysis} narrative={narrative} answers={answers} onEdit={() => setStep("describe")} onRestart={restart}
            onEditDetails={editDetails} />
        )}
      </main>

      <footer className="border-t border-ink/10 bg-white">
        <div className={`${WRAP} grid gap-4 py-8 text-xs leading-relaxed text-slate md:grid-cols-3`}>
          <div className="flex items-start gap-3 md:col-span-2">
            <Logo />
            <div><p>{analysis?.disclaimer || t.disclaimer}</p><p className="mt-2">{t.footer_mapping}</p></div>
          </div>
          <div className="md:text-right print:hidden">
            <p className="font-semibold text-ink">{t.helplines_title}</p>
            <p className="mt-1">112 · 1930 (cyber) · 181 (women) · 15100 (legal aid)</p>
          </div>
        </div>
      </footer>

      {tool && <Drawer tool={tool} t={t} lang={lang} onClose={() => setTool(null)} onTool={setTool} />}
    </div>
  );
}
