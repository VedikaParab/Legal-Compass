"""Turn an uploaded FIR / charge-sheet / complaint into text, then convert its citations.

Supported: PDF with a text layer (pypdf), Word .docx (python-docx), .txt, and scanned PDFs / photos via OCR
(Tesseract, optional — install it plus the Hindi/Marathi language packs for Devanagari documents).
Files are processed in memory only and never written to disk or logged.
"""
from __future__ import annotations

import contextvars
import io
import re

from . import lc_client

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 30
MIN_TEXT_PER_PAGE = 40      # below this a PDF page is treated as a scan and sent to OCR


class DocumentError(ValueError):
    pass


class NeedsOCR(DocumentError):
    """A scan or photo and no server-side OCR: the browser does the OCR instead (Tesseract.js)."""


def _find_tesseract():
    """Use TESSERACT_CMD, else the standard Windows install folders, else whatever is on PATH."""
    import os
    import shutil

    import pytesseract
    candidates = [os.environ.get("TESSERACT_CMD", ""),
                  r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")]
    for c in candidates:
        if c and os.path.isfile(c):
            pytesseract.pytesseract.tesseract_cmd = c
            return c
    return shutil.which("tesseract")


def _ocr_langs() -> str | None:
    import os
    if os.environ.get("SERVER_OCR", "1") == "0":  # e.g. on free hosting: the browser does OCR instead
        return None
    try:
        import pytesseract
        if not _find_tesseract():
            return None
        have = set(pytesseract.get_languages(config=""))
    except Exception:
        return None
    langs = [l for l in ("eng", "hin", "mar") if l in have]
    return "+".join(langs) if langs else None


def ocr_status() -> dict:
    langs = _ocr_langs()
    out = {"available": bool(langs), "languages": langs.split("+") if langs else []}
    if not langs:
        out["help"] = ("Install Tesseract (UB Mannheim build for Windows) with the Hindi and Marathi language data, "
                       "then restart the backend. If it is installed elsewhere, set TESSERACT_CMD to tesseract.exe.")
    return out


# Tesseract language the current upload needs ("hin"/"mar" when the site is in Hindi/Marathi)
_NEEDED_LANG: contextvars.ContextVar[str | None] = contextvars.ContextVar("needed_lang", default=None)


def _server_can_ocr() -> bool:
    """Server OCR only if Tesseract is installed AND has the language this document needs; else the browser does it."""
    langs = _ocr_langs()
    need = _NEEDED_LANG.get()
    return bool(langs) and (need is None or need in langs.split("+"))


def _ocr_image(img) -> str:
    import pytesseract
    langs = _ocr_langs()
    if not _server_can_ocr():
        raise NeedsOCR("This looks like a scanned document or photo; it will be read in your browser instead.")
    return pytesseract.image_to_string(img, lang=langs)


def _pdf(data: bytes) -> tuple[str, dict]:
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as e:
        raise DocumentError(f"Could not read this PDF ({type(e).__name__}).") from e
    if reader.is_encrypted:
        raise DocumentError("This PDF is password-protected. Remove the password and upload again.")
    pages = reader.pages[:MAX_PAGES]
    texts, ocr_pages = [], 0
    for page in pages:
        t = page.extract_text() or ""
        if len(t.strip()) < MIN_TEXT_PER_PAGE:
            imgs = []
            try:
                imgs = [im.image for im in page.images]
            except Exception:
                pass
            if imgs:
                t = fix_ocr("\n".join(_ocr_image(im) for im in imgs))
                ocr_pages += 1
            elif not _server_can_ocr():
                raise NeedsOCR("This PDF page has no text layer; it will be read in your browser instead.")
        texts.append(t)
    info = {"pages": len(reader.pages), "pages_read": len(pages), "ocr_pages": ocr_pages}
    if len(reader.pages) > MAX_PAGES:
        info["note"] = f"Only the first {MAX_PAGES} pages were read."
    return "\n\n".join(texts), info


def _docx(data: bytes) -> tuple[str, dict]:
    from docx import Document
    try:
        d = Document(io.BytesIO(data))
    except Exception as e:
        raise DocumentError("Could not read this Word file. Save it as .docx and try again.") from e
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return "\n".join(parts), {}


def _image(data: bytes) -> tuple[str, dict]:
    from PIL import Image, ImageOps
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("L")
    except Exception as e:
        raise DocumentError("Could not open this image.") from e
    if max(img.size) < 1500:  # small phone photos OCR better when upscaled
        f = 1500 / max(img.size)
        img = img.resize((int(img.width * f), int(img.height * f)))
    return fix_ocr(_ocr_image(img)), {"ocr_pages": 1}


def extract_text(filename: str, data: bytes, lang: str = "en") -> dict:
    _NEEDED_LANG.set(None)  # English-only OCR for now; set {"hi": "hin", "mr": "mar"}.get(lang) to route Hindi/Marathi scans to the browser
    if len(data) > MAX_BYTES:
        raise DocumentError("File is larger than 10 MB.")
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        text, info, kind = *_pdf(data), "pdf"
    elif name.endswith(".docx"):
        text, info, kind = *_docx(data), "docx"
    elif name.endswith((".txt", ".text")):
        text, info, kind = data.decode("utf-8", errors="replace"), {}, "text"
    elif name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")):
        text, info, kind = *_image(data), "image"
    elif name.endswith(".doc"):
        raise DocumentError("Old .doc files are not supported. Save the file as .docx or PDF.")
    else:
        raise DocumentError("Unsupported file type. Upload a PDF, .docx, .txt or a photo (JPG/PNG).")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 20:
        if kind == "pdf":
            raise NeedsOCR("No text layer found in this PDF; it will be read in your browser instead.")
        raise DocumentError("No readable text was found in this file. If it is a photo, make sure it is sharp and well lit.")
    return {"kind": kind, "text": text, "chars": len(text), **info}


OCR_FIXES = [
    # common Tesseract misreadings of code names next to section numbers
    (re.compile(r"(?<=[\d/ ])(?:[TlI1|!]\s?P\s?[CGc]|I\s?P\s?G|1PC|lPC)\b"), "IPC"),
    (re.compile(r"\b(?:Cr\s?[.,]?\s?P\s?[.,]?\s?[CG]|CrPG|CRPC)\b"), "CrPC"),
    (re.compile(r"\bB\s?N\s?S\s?S\b"), "BNSS"),
    (re.compile(r"[०-९]"), lambda m: str("०१२३४५६७८९".index(m.group(0)))),  # Devanagari digits
]


def fix_ocr(text: str) -> str:
    for rx, rep in OCR_FIXES:
        text = rx.sub(rep, text)
    return text


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text or "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def convert_citations(text: str) -> dict:
    """Old ↔ new citations via the existing LegalCompass API (/v1/convert/text)."""
    try:
        r = lc_client.convert_text(text)
    except lc_client.LegalCompassUnavailable as e:
        return {"available": False, "error": str(e), "citations": [], "converted_text": None}
    cits = []
    for c in r.get("citations", []):
        cits.append({"found": c["text"].strip(), "code": c["code"], "target_code": c.get("target_code"),
                     "suggestion": c.get("suggestion"), "ambiguous": c.get("ambiguous", False),
                     "items": [{"section": it["section"], "status": it["status"], "targets": it["targets"],
                                "notes": it.get("notes", [])[:1]} for it in c.get("items", [])]})
    return {"available": True, "citations": cits, "converted_text": r.get("converted_text"),
            "needs_attention": sum(1 for c in cits if c["ambiguous"])}


def conversion_advice(regime: dict, offence_date: str | None, lang: str = "en") -> dict:
    """Whether the converted (new-code) citations are the ones that actually apply to this document."""
    out = _advice_en(regime, offence_date)
    if lang in ("hi", "mr"):
        from . import i18n
        key = out["law"] or ("needs_review" if regime.get("decision") == "needs_review" else "none")
        out["message"], out["procedure"] = i18n.advice(key, lang, offence_date)
    return out


def _advice_en(regime: dict, offence_date: str | None) -> dict:
    law, decision = regime.get("law"), regime.get("decision")
    proc = ("Procedural sections (CrPC/BNSS) follow the date the proceedings began: if this FIR was registered "
            "before 1 July 2024, the CrPC continues to apply to it.")
    if decision == "decided" and law == "IPC":
        return {"level": "warning", "law": "IPC", "offence_date": offence_date,
                "message": f"The offence date in this document ({offence_date}) is before 1 July 2024, so the IPC "
                           "sections remain the applicable law. The BNS numbers below are shown for reference only — "
                           "do not replace the IPC sections in this case.", "procedure": proc}
    if decision == "decided" and law == "BNS":
        return {"level": "ok", "law": "BNS", "offence_date": offence_date,
                "message": f"The offence date in this document ({offence_date}) is on or after 1 July 2024, so the "
                           "new codes apply and old IPC citations should be read as their BNS counterparts.",
                "procedure": proc}
    if decision == "needs_review":
        return {"level": "warning", "law": None, "offence_date": offence_date,
                "message": "The conduct described spans 1 July 2024, so both codes may apply. Use the conversions "
                           "below as a guide and have a lawyer confirm.", "procedure": proc}
    return {"level": "info", "law": None, "offence_date": None,
            "message": "No offence date was found in this document. The applicable code depends on when the offence "
                       "was committed: before 1 July 2024 the IPC applies, on or after it the BNS.", "procedure": proc}


OCR_CHECK = {
    "en": "This text was read from a scan, which can misread numbers. Check the date ({d}) and section numbers against your document.",
    "hi": "यह टेक्स्ट स्कैन से पढ़ा गया है, जिसमें अंक गलत पढ़े जा सकते हैं। तारीख ({d}) और धाराओं को अपने दस्तावेज़ से मिला लें।",
    "mr": "हा मजकूर स्कॅनमधून वाचला आहे, त्यात आकडे चुकीचे वाचले जाऊ शकतात. तारीख ({d}) आणि कलमे तुमच्या दस्तऐवजाशी जुळवून पहा.",
}
