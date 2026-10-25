# Put the demo online (free): Vercel + Render

The website goes on **Vercel**; the backend and the mapping API run together as **one Render service**.
OCR for photos and scans runs in the visitor's browser (Tesseract.js), so nothing has to be installed anywhere.
Total cost: ₹0. Time: about 20 minutes.

```
Browser ──▶ Vercel (website, OCR in the browser)
   └──────▶ Render (assistant backend + mapping API in one container)
```

## What you need
- A GitHub account (free), a Render account (free, sign in with GitHub) and a Vercel account (free, sign in with GitHub).
- This `legalcompass-app` folder.

## 1. Put the code on GitHub
1. On github.com click **New repository** → name it `legalcompass-app` → **Private** is fine → *Create*.
2. In PowerShell, inside the `legalcompass-app` folder:
   ```powershell
   git init
   git add .
   git commit -m "LegalCompass assistant demo"
   git branch -M main
   git remote add origin https://github.com/<your-username>/legalcompass-app.git
   git push -u origin main
   ```
   `.gitignore` already keeps out `node_modules`, build output and your IL-TUR files (`backend/data/*.joblib`),
   which must never be uploaded (the IL-TUR licence forbids redistribution).

## 2. Backend on Render
1. On render.com: **New → Blueprint** → connect GitHub → pick `legalcompass-app`.
2. Render reads `render.yaml` and creates **legalcompass-backend** (Docker, free plan). Click **Apply**.
3. The first build takes 5–10 minutes. When it says *Live*, copy its URL, e.g.
   `https://legalcompass-backend.onrender.com`.
4. Check it: open `https://legalcompass-backend.onrender.com/api/status` — you should see `"legalcompass_api": true`.

## 3. Website on Vercel
1. On vercel.com: **Add New → Project** → import `legalcompass-app`.
2. **Root Directory:** click *Edit* and choose `web`. Framework is detected as Next.js.
3. **Environment Variables:** add
   `NEXT_PUBLIC_API_BASE` = your Render URL from step 2 (no trailing slash).
4. Click **Deploy**. You get a link like `https://legalcompass-app.vercel.app` — that is your demo.

The backend already allows any `*.vercel.app` address (see `CORS_ORIGIN_REGEX` in `render.yaml`). If you later use
your own domain, add it in Render → Environment → `CORS_ORIGINS` (comma-separated).

## On demo day
- **Free Render services sleep after ~15 minutes without visitors.** The first request then takes up to a minute;
  the website shows "Starting the demo server…" meanwhile. Open the site **2–3 minutes before** you present.
- The free plan includes 750 hours a month, enough for one always-used service.
- Photos and scanned PDFs are read in the browser. The first scan downloads the OCR language data (3–5 MB) once.
  For Hindi or Marathi documents, switch the site language first.
- Limits for the public link: 40 analyses, 12 uploads and 12 drafts per minute per visitor.

## What the online demo does not include
- **IL-TUR features** (classifier suggestions, similar past cases) — your trained files stay on your laptop because
  IL-TUR may not be redistributed. The demo says "not set up on this server". Show those features from your laptop.
- The LLM wording is optional: add `LLM_API_KEY` (your xAI Grok `xai-...` or Groq `gsk_...` key) in Render → Environment.
  Without IL-TUR on Render it adds the plain-language explanation only.

## Updating the demo
Push to GitHub (`git add . ; git commit -m "update" ; git push`). Render and Vercel redeploy automatically.

## Troubleshooting
| Problem | Fix |
|---|---|
| Website shows "server is busy" for a long time | Open the Render URL `/api/status` directly; check Render → Logs |
| Browser console shows a CORS error | Add your exact website address to Render → Environment → `CORS_ORIGINS` and redeploy |
| `/api/status` shows `"legalcompass_api": false` | Render → Logs: the mapping API failed to start (look for an error above "mapping API ready") |
| Uploads say "Too many requests" | Wait a minute, or raise `RATE_DOC` in Render → Environment |
| Vercel build fails at "copy-ocr-assets" | Make sure Root Directory is `web` and `package-lock.json` is committed |
