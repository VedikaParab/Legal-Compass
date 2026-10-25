// In-browser OCR: Tesseract.js for photos and scanned PDFs, so no OCR software is needed on any computer or server.
// The image never leaves the user's device; only the recognised text is sent to the backend.
import type { Lang } from "./i18n";

const LANGS: Record<Lang, string> = { en: "eng", hi: "hin+eng", mr: "mar+eng" };
const MAX_PDF_PAGES = 10;

export type OcrProgress = (message: string, fraction: number) => void;

async function makeWorker(lang: Lang, onProgress?: OcrProgress) {
  const { createWorker } = await import("tesseract.js");
  return createWorker(LANGS[lang], 1, {
    workerPath: "/ocr/worker.min.js",
    corePath: "/ocr/core",
    langPath: "/ocr/lang",
    logger: (m: { status: string; progress: number }) => onProgress?.(m.status, m.progress ?? 0),
  });
}

export async function ocrImage(file: Blob, lang: Lang, onProgress?: OcrProgress): Promise<string> {
  const worker = await makeWorker(lang, onProgress);
  try {
    const { data } = await worker.recognize(file);
    return data.text;
  } finally {
    await worker.terminate();
  }
}

export async function ocrPdf(file: File, lang: Lang, onProgress?: OcrProgress): Promise<{ text: string; pages: number; read: number }> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = "/ocr/pdf.worker.min.mjs";
  const pdf = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
  const n = Math.min(pdf.numPages, MAX_PDF_PAGES);
  const worker = await makeWorker(lang);
  const texts: string[] = [];
  try {
    for (let i = 1; i <= n; i++) {
      onProgress?.(`page ${i} / ${n}`, (i - 1) / n);
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale: 2 });
      const canvas = document.createElement("canvas");
      canvas.width = viewport.width; canvas.height = viewport.height;
      await page.render({ canvasContext: canvas.getContext("2d")!, viewport }).promise;
      const { data } = await worker.recognize(canvas);
      texts.push(data.text);
    }
  } finally {
    await worker.terminate();
  }
  onProgress?.("done", 1);
  return { text: texts.join("\n\n"), pages: pdf.numPages, read: n };
}

export const isImage = (f: File) => f.type.startsWith("image/") || /\.(png|jpe?g|webp|tiff?|bmp)$/i.test(f.name);
