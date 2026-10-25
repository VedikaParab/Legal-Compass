"""SanhitaBridge public API (reference implementation).

Run:   PYTHONPATH=src uvicorn sb_api.main:app --reload
Docs:  http://localhost:8000/docs   (OpenAPI JSON at /openapi.json)
"""
from __future__ import annotations

import csv
import io
import os
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import __version__
from .citations import convert_citation, convert_text, find_citations
from .store import CODE_NAMES, DATASET_META, canon_code, get_store
from .temporal import applicable_law

app = FastAPI(
    title="SanhitaBridge API",
    version=__version__,
    description="Look up how India's repealed criminal codes (IPC, CrPC, IEA) map to the new codes (BNS, BNSS, BSA), "
                "convert citations in documents, compare old and new text, and decide which law applies by date. "
                f"Dataset DOI {DATASET_META['doi']} ({DATASET_META['licence']}). {DATASET_META['disclaimer']}",
)
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("SB_CORS", "*").split(","), allow_methods=["*"],
                   allow_headers=["*"])

# ---------------------------------------------------------------- auth + rate limit (simple, in-process)
API_KEYS = {k for k in os.environ.get("SB_API_KEYS", "").split(",") if k}
ANON_PER_MIN = int(os.environ.get("SB_RATE_ANON", "60"))
KEY_PER_MIN = int(os.environ.get("SB_RATE_KEY", "600"))
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request):
    key = request.headers.get("x-api-key")
    if key and API_KEYS and key not in API_KEYS:
        raise HTTPException(401, "invalid API key")
    ident, limit = (f"key:{key}", KEY_PER_MIN) if key else (f"ip:{request.client.host if request.client else '?'}",
                                                            ANON_PER_MIN)
    now, q = time.time(), _hits[ident]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, f"rate limit {limit}/min exceeded; request an API key for higher limits")
    q.append(now)


@app.exception_handler(KeyError)
@app.exception_handler(ValueError)
async def bad_input(_, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc).strip("'\"")})


R = [Depends(rate_limit)]


# ---------------------------------------------------------------- models
class TextIn(BaseModel):
    text: str = Field(..., max_length=200_000, examples=["Accused booked u/s 420/34 IPC and 66D IT Act; FIR under Section 154 Cr.P.C."])
    annotate_original: bool = True


class BatchIn(BaseModel):
    citations: list[str] = Field(..., max_length=1000, examples=[["IPC 302", "CrPC 438", "IEA 65B", "BNS 318(4)"]])


# ---------------------------------------------------------------- meta
@app.get("/v1/meta", tags=["meta"])
def meta():
    """Dataset name, DOI, licence, citation text, disclaimer, API version."""
    st = get_store()
    return {**DATASET_META, "api_version": __version__, "codes": CODE_NAMES, "rows": len(st.rows)}


@app.get("/v1/stats", tags=["meta"], dependencies=R)
def stats():
    return get_store().stats()


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}


# ---------------------------------------------------------------- mapping
@app.get("/v1/map/{code}/{section}", tags=["mapping"], dependencies=R)
def map_section(code: str, section: str):
    """Old code -> new provisions (IPC/CrPC/IEA) or new code -> old provisions (BNS/BNSS/BSA).
    Section may include a sub-section, e.g. `376(2)` or `498A`."""
    return get_store().lookup(code, section)


@app.get("/v1/rows/{row_id}", tags=["mapping"], dependencies=R)
def get_row(row_id: str):
    r = get_store().row(row_id)
    if not r:
        raise HTTPException(404, f"no row {row_id}")
    return r


@app.get("/v1/compare/{row_id}", tags=["mapping"], dependencies=R)
def compare(row_id: str):
    """Old and new provision text side by side with a word-level diff."""
    r = get_store().compare(row_id)
    if not r:
        raise HTTPException(404, f"no row {row_id}")
    return r


@app.post("/v1/map/batch", tags=["mapping"], dependencies=R)
def map_batch(body: BatchIn):
    """Map up to 1000 citations like 'IPC 302' or 'Section 154 CrPC' in one call."""
    out = []
    for c in body.citations:
        found = find_citations(c)
        if not found:
            out.append({"input": c, "error": "no citation recognised"})
            continue
        for f in found:
            out.append({"input": c, **convert_citation(f["code"], f["sections"])})
    return {"results": out}


# ---------------------------------------------------------------- statute text + search
@app.get("/v1/sections/{code}/{section}", tags=["statutes"], dependencies=R)
def section_text(code: str, section: str):
    c = canon_code(code)
    s = get_store().section(c, section.upper().replace("-", ""))
    if not s:
        raise HTTPException(404, f"{c} {section} not found")
    return s


@app.get("/v1/search", tags=["statutes"], dependencies=R)
def search(q: str = Query(..., min_length=2, examples=["cheating"]), code: str | None = None,
           limit: int = Query(20, ge=1, le=100)):
    """Keyword search over section titles and text (e.g. 'cheating', 'anticipatory bail', 'electronic record')."""
    return {"query": q, "results": get_store().search(q, code, limit)}


# ---------------------------------------------------------------- documents
@app.post("/v1/convert/text", tags=["documents"], dependencies=R)
def convert(body: TextIn):
    """Find every IPC/CrPC/IEA (or BNS/BNSS/BSA) citation in a passage and rewrite it; ambiguous ones are flagged."""
    return convert_text(body.text, body.annotate_original)


@app.post("/v1/citations/extract", tags=["documents"], dependencies=R)
def extract(body: TextIn):
    return {"citations": find_citations(body.text)}


# ---------------------------------------------------------------- temporal
@app.get("/v1/applicable-law", tags=["temporal"], dependencies=R)
def which_law(offence_date: date | None = None, offence_end_date: date | None = None,
              proceedings_start_date: date | None = None):
    """Which penal, procedural and evidence law applies, given the offence date and the date proceedings began."""
    return applicable_law(offence_date, offence_end_date, proceedings_start_date)


# ---------------------------------------------------------------- export
@app.get("/v1/export", tags=["export"], dependencies=R)
def export(format: str = Query("json", pattern="^(json|csv)$"), pair: str | None = None):
    """Full dataset (or one code pair: IPC_to_BNS, CrPC_to_BNSS, IEA_to_BSA) as JSON or CSV."""
    rows = get_store().export_rows(pair)
    if format == "json":
        return {"meta": DATASET_META, "rows": rows}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=sanhitabridge_{pair or 'all'}.csv"})
