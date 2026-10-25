"use client";

import { useState } from "react";
import { NeedsOcr, sendDocumentText, uploadDocument } from "@/lib/api";
import { isImage, ocrImage, ocrPdf } from "@/lib/ocr";
import type { DocResult } from "@/lib/types";
import type { Lang, T } from "@/lib/i18n";

export default function DocumentUpload({ t, lang, onUse }: { t: T; lang: Lang; onUse: (text: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [res, setRes] = useState<DocResult | null>(null);
  const [showText, setShowText] = useState(false);

  const onProgress = (status: string, frac: number) =>
    setProgress(`${t.ocr_reading} ${status.startsWith("page") ? status : ""} ${Math.round(frac * 100)}%`.replace(/\s+/g, " "));

  const pick = async (f: File | undefined) => {
    if (!f) return;
    setBusy(true); setError(""); setRes(null); setProgress("");
    try {
      if (f.size > 10 * 1024 * 1024) throw new Error("File is larger than 10 MB.");
      if (isImage(f)) {
        // photos are read in the browser (works everywhere, the image never leaves the device)
        setRes(await sendDocumentText(await ocrImage(f, lang, onProgress), f.name, lang));
      } else {
        try {
          setRes(await uploadDocument(f, lang));
        } catch (e) {
          if (!(e instanceof NeedsOcr)) throw e;
          const o = await ocrPdf(f, lang, onProgress);   // scanned PDF: OCR page by page in the browser
          setRes(await sendDocumentText(o.text, f.name, lang, o.pages, o.read));
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false); setProgress("");
    }
  };

  const tone = res?.advice.level === "ok" ? "bg-mist text-ink" : res?.advice.level === "warning" ? "bg-amber-soft text-ink" : "bg-mist text-ink";

  return (
    <div>
      <p className="mt-1 text-slate">{t.upload_help}</p>
      <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-ink/20 bg-mist/40 px-4 py-8 text-center hover:border-sky">
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-8 w-8 text-ink-2" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="mt-2 font-semibold text-ink">{busy ? (progress || t.uploading) : t.choose_file}</span>
        <span className="text-xs text-slate">PDF · DOCX · TXT · JPG · PNG (max 10 MB)</span>
        <span className="mt-1 text-xs text-slate">{t.ocr_hint}</span>
        <input type="file" className="sr-only" disabled={busy}
          accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp,.tif,.tiff,application/pdf,image/*"
          onChange={(e) => pick(e.target.files?.[0])} />
      </label>
      {error && <p role="alert" className="mt-3 rounded-xl bg-amber-soft p-3 text-sm text-warn">{error}</p>}

      {res && (
        <div className="mt-5 space-y-4">
          <p className="text-sm text-slate">
            ✓ {t.doc_read}{res.document.pages ? ` · ${res.document.pages} ${t.pages}` : ""}{res.document.ocr_pages ? ` · ${t.ocr_used}` : ""}
            {res.document.note ? ` · ${res.document.note}` : ""}
          </p>
          <div className={`rounded-xl p-4 text-sm ${tone}`}>
            <p className="font-semibold">{res.advice.message}</p>
            <p className="mt-1 text-slate">{res.advice.procedure}</p>
            {res.advice.ocr_check && <p className="mt-2 font-medium text-warn">⚠ {res.advice.ocr_check}</p>}
          </div>

          <div>
            <h3 className="font-semibold text-ink">{t.citations_found}</h3>
            {!res.citations.available && <p className="mt-1 text-sm text-warn">{res.citations.error}</p>}
            {res.citations.available && res.citations.citations.length === 0 && <p className="mt-1 text-sm text-slate">{t.no_citations}</p>}
            <ul className="mt-2 space-y-2">
              {res.citations.citations.map((c, i) => (
                <li key={i} className="rounded-lg border border-ink/10 p-3 text-sm">
                  <span className="font-mono text-ink-2">{c.found}</span>
                  {c.suggestion ? (
                    <> <span className="text-slate">→ {t.becomes}</span> <span className="font-semibold text-ink">{c.suggestion}</span></>
                  ) : (
                    <div className="mt-1 text-warn">
                      {t.choose_needed}{" "}
                      {c.items.map((it) => `${c.code} ${it.section} → ${it.targets.join(" / ") || "—"}`).join("; ")}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {res.citations.converted_text && (
            <div>
              <button type="button" onClick={() => setShowText(!showText)} className="text-sm font-medium text-ink-2 underline-offset-4 hover:underline">
                {showText ? "▾" : "▸"} {t.show_converted}
              </button>
              {showText && <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-xl bg-mist/60 p-4 text-sm text-ink">{res.citations.converted_text}</pre>}
            </div>
          )}

          <button type="button" onClick={() => onUse(res.narrative)}
            className="rounded-xl bg-ink px-6 py-3 font-semibold text-white hover:bg-ink-2">{t.use_document}</button>
        </div>
      )}
    </div>
  );
}
