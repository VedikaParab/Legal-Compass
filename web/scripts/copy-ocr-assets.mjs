// Copies the in-browser OCR engine (Tesseract.js), its English/Hindi/Marathi language data and the pdf.js worker
// into public/ocr, so the website serves them itself (no third-party CDN). Runs before `dev` and `build`.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const out = join(process.cwd(), "public", "ocr");
const pkg = (name) => dirname(require.resolve(`${name}/package.json`));
mkdirSync(join(out, "core"), { recursive: true });
mkdirSync(join(out, "lang"), { recursive: true });

cpSync(join(pkg("tesseract.js"), "dist", "worker.min.js"), join(out, "worker.min.js"));
for (const f of ["tesseract-core-lstm.wasm.js", "tesseract-core-simd-lstm.wasm.js", "tesseract-core-lstm.wasm", "tesseract-core-simd-lstm.wasm",
                 "tesseract-core-lstm.js", "tesseract-core-simd-lstm.js"]) {
  const src = join(pkg("tesseract.js-core"), f);
  if (existsSync(src)) cpSync(src, join(out, "core", f));
}
for (const l of ["eng", "hin", "mar"]) {
  cpSync(join(pkg(`@tesseract.js-data/${l}`), "4.0.0_best_int", `${l}.traineddata.gz`), join(out, "lang", `${l}.traineddata.gz`));
}
cpSync(join(pkg("pdfjs-dist"), "build", "pdf.worker.min.mjs"), join(out, "pdf.worker.min.mjs"));
console.log("OCR assets copied to public/ocr");
