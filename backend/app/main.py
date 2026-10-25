"""LegalCompass Assistant — backend orchestrator.

Run:  uvicorn app.main:app --port 8100 --reload      (needs the LegalCompass API on LEGALCOMPASS_API)
"""
from __future__ import annotations

import os
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fastapi.responses import Response

from . import __version__, cases, classifier, complaint, config, documents, extract, lc_client, llm, pipeline
from .offences import OFFENCES

app = FastAPI(title="LegalCompass Assistant API", version=__version__,
              description="Describe an incident, answer a few questions, and get the applicable code (IPC or BNS by "
                          "date), possibly applicable sections with their old/new counterparts, similar cases and next "
                          "steps. Uses the LegalCompass mapping (DOI 10.21227/h4wg-7413). Not legal advice.")
# ---------------------------------------------------------------- simple per-IP rate limits (public demo)
LIMITS = {"analyze": int(os.environ.get("RATE_ANALYZE", "40")), "doc": int(os.environ.get("RATE_DOC", "12")),
          "complaint": int(os.environ.get("RATE_COMPLAINT", "12")), "lookup": int(os.environ.get("RATE_LOOKUP", "90"))}
_hits: dict[str, deque] = defaultdict(deque)


def limit(bucket: str):
    def dep(request: Request):
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "?")
        q, now = _hits[f"{bucket}:{ip}"], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= LIMITS[bucket]:
            raise HTTPException(429, "Too many requests — please wait a minute and try again.")
        q.append(now)
    return dep


WARMUP = {"state": "starting", "seconds": None}


def _warm():
    """Load the optional IL-TUR classifier and case index once at startup (they are large), not on the first request."""
    t = time.time()
    WARMUP["state"] = "loading"
    try:
        if classifier.available():
            classifier.predict("warm up the classifier")
        if cases.available():
            cases.similar("warm up the case index", [])
        WARMUP["state"] = "ready"
    except Exception as e:  # never stop the server because an optional model failed
        WARMUP["state"] = f"failed: {type(e).__name__}: {e}"[:200]
    WARMUP["seconds"] = round(time.time() - t, 1)
    print(f"[legalcompass] optional models {WARMUP['state']} in {WARMUP['seconds']}s", flush=True)


@app.on_event("startup")
def _startup():
    threading.Thread(target=_warm, daemon=True).start()


app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_origin_regex=config.CORS_ORIGIN_REGEX or None,
                   allow_methods=["*"], allow_headers=["*"])


class AnalyzeIn(BaseModel):
    narrative: str = Field(..., min_length=10, max_length=8000,
                           examples=["On 12 March 2025 someone called pretending to be from my bank and I lost Rs 45,000 through UPI."])
    answers: dict[str, str] = Field(default_factory=dict)
    finalize: bool = Field(False, description="Return the analysis even if some questions are unanswered")
    lang: str = Field("en", pattern="^(en|hi|mr)$", description="Language for questions and guidance")


@app.post("/api/analyze", dependencies=[Depends(limit("analyze"))])
def analyze(body: AnalyzeIn):
    # The narrative is processed in memory only; nothing is stored or logged.
    return pipeline.analyze(body.narrative, body.answers, body.finalize, body.lang)


class ComplaintIn(BaseModel):
    narrative: str = Field(..., min_length=10, max_length=8000)
    answers: dict[str, str] = Field(default_factory=dict)
    kind: str = Field("fir", pattern="^(fir|sp|magistrate)$")


@app.post("/api/complaint", dependencies=[Depends(limit("complaint"))])
def complaint_draft(body: ComplaintIn):
    """A .docx complaint draft (police station / SP / Magistrate). Generated in memory; nothing is stored."""
    analysis = pipeline.analyze(body.narrative, body.answers, finalize=True)
    data, name = complaint.build(body.kind, body.narrative, analysis)
    return Response(content=data, headers={"Content-Disposition": f'attachment; filename="{name}"'},
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def _process_document(doc: dict, lang: str) -> dict:
    if doc.get("kind") == "browser-ocr":
        doc["text"] = documents.fix_ocr(doc["text"])
    conv = documents.convert_citations(doc["text"])
    facts = extract.extract(doc["text"])
    regime, _ = pipeline._regime(facts["inferred"], facts["facts"].get("ongoing_since_year"))
    return {"document": {k: v for k, v in doc.items() if k != "text"}, "text": doc["text"],
            "citations": conv, "facts": facts["facts"], "inferred": facts["inferred"],
            "advice": {**documents.conversion_advice(regime, facts["inferred"].get("offence_date"), lang),
                       **({"ocr_check": documents.OCR_CHECK.get(lang, documents.OCR_CHECK["en"]).format(
                           d=facts["inferred"].get("offence_date", "—"))} if doc.get("ocr_pages") else {})},
            "narrative": doc["text"][:7500]}


@app.post("/api/document", dependencies=[Depends(limit("doc"))])
async def document(file: UploadFile = File(...), lang: str = "en"):
    """Read an FIR / charge-sheet / complaint (PDF, DOCX, TXT or photo) and convert its old citations.

    Processed in memory only; the file is not stored or logged. A scan with no server OCR returns
    422 {"code": "needs_ocr"} and the website OCRs it in the browser, then calls /api/document-text.
    """
    data = await file.read(documents.MAX_BYTES + 1)
    try:
        doc = documents.extract_text(file.filename or "", data, lang)
    except documents.NeedsOCR as e:
        raise HTTPException(status_code=422, detail={"code": "needs_ocr", "message": str(e)})
    except documents.DocumentError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _process_document(doc, lang)


class DocTextIn(BaseModel):
    text: str = Field(..., min_length=20, max_length=200_000)
    filename: str = ""
    pages: int | None = None
    pages_read: int | None = None
    lang: str = Field("en", pattern="^(en|hi|mr)$")


@app.post("/api/document-text", dependencies=[Depends(limit("doc"))])
def document_text(body: DocTextIn):
    """Text recognised in the browser (Tesseract.js) from a photo or scanned PDF."""
    text = documents.clean_text(body.text)
    if len(text) < 20:
        raise HTTPException(status_code=422, detail="No readable text was found. Make sure the photo is sharp and well lit.")
    doc = {"kind": "browser-ocr", "text": text, "chars": len(text), "ocr_pages": body.pages_read or 1,
           **({"pages": body.pages} if body.pages else {})}
    if body.pages and body.pages_read and body.pages > body.pages_read:
        doc["note"] = f"Only the first {body.pages_read} pages were read."
    return _process_document(doc, body.lang)


CODES = {"IPC": "IPC", "BNS": "BNS", "CRPC": "CrPC", "BNSS": "BNSS", "IEA": "IEA", "BSA": "BSA"}
_Q = re.compile(r"^\s*(?:(ipc|bns|crpc|cr\.?p\.?c\.?|bnss|iea|bsa)\b)?\s*(?:s(?:ec(?:tion)?)?\.?\s*)?([0-9]{1,3}[a-z]{0,2}(?:\s*\(\s*[0-9a-z]+\s*\))*)\s*(?:(ipc|bns|crpc|bnss|iea|bsa))?\s*$", re.I)


@app.get("/api/lookup", dependencies=[Depends(limit("lookup"))])
def lookup(q: str):
    """Quick converter: '420', 'IPC 302', 'BNS 103(1)', '154 CrPC' -> the corresponding old/new provisions."""
    m = _Q.match(q.strip())
    if not m:
        raise HTTPException(422, "Type a section like 420, IPC 302, BNS 103 or CrPC 154.")
    code = (m.group(1) or m.group(3) or "IPC").upper().replace(".", "")
    code = CODES.get(code, "IPC")
    sec = re.sub(r"\s+", "", m.group(2)).upper()
    base = re.match(r"[0-9]+[A-Z]*", sec).group(0)
    try:
        r = lc_client.lookup(code, base)
    except lc_client.LegalCompassUnavailable as e:
        raise HTTPException(503, str(e))
    if not r or not r.get("results"):
        return {"code": code, "section": base, "found": False, "results": [],
                "message": f"{code} {base} is not in the mapping. Check the number (sections that were repealed have no counterpart)."}
    rows = [{"old": x["old"].get("provision"), "old_heading": x["old"].get("heading"),
             "new": x["new"].get("provision"), "new_heading": x["new"].get("heading"),
             "change": x.get("substantive_change"), "change_explained": x.get("substantive_change_explained", ""),
             "mapping_explained": x.get("mapping_type_explained", ""), "notes": x.get("notes") or "", "row_id": x.get("row_id")}
            for x in r["results"]]
    return {"code": code, "section": base, "found": True, "direction": r.get("direction"), "target_code": r.get("target_code"),
            "status": r.get("status"), "message": r.get("message", ""), "results": rows[:12]}


@app.get("/api/applicable-law", dependencies=[Depends(limit("lookup"))])
def applicable_law(date: str, lang: str = "en"):
    """Which penal code applies to an offence on this date (IPC before 1 July 2024, BNS on or after)."""
    regime, procedure = pipeline._regime({"offence_date": date})
    return {"date": date, "law": regime.get("law"), "decision": regime.get("decision"),
            "reason": pipeline.i18n.regime_reason(regime, pipeline.i18n.lang_of(lang)), "commencement": "2024-07-01"}


@app.get("/api/status")
def status():
    api = lc_client.check()
    return {"version": __version__, "legalcompass_api": api["ok"], "legalcompass_api_url": api["url"],
            **({"legalcompass_api_error": api["error"]} if not api["ok"] else {}), "classifier": classifier.available(),
            "case_index": cases.available(), "models": WARMUP, "ocr": documents.ocr_status(), "llm": llm.status(), "offence_types": len(OFFENCES)}


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}
