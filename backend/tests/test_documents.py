"""Document upload: PDF, DOCX, photo (OCR), citation conversion and the date-based advice."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import documents, lc_client
from app.main import app

c = TestClient(app)
FIX = Path(__file__).parent / "fixtures"
pytestmark = pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")


def upload(name, data=None):
    return c.post("/api/document", files={"file": (name, data if data is not None else (FIX / name).read_bytes())})


@pytest.mark.parametrize("name", ["fir_sample.pdf", "fir_sample.docx"] +
                         (["fir_scan.png"] if documents.ocr_status()["available"] else []))
def test_reads_and_converts(name):
    j = upload(name).json()
    sugg = {x["found"]: x["suggestion"] for x in j["citations"]["citations"]}
    assert sugg["u/s 420/34 IPC"] == "u/s 318(4)/3(5) BNS"
    assert any(x["ambiguous"] and "498" in x["found"] for x in j["citations"]["citations"])
    assert j["inferred"]["offence_date"] == "2024-02-14"
    # offence before the reform: the IPC sections stay the applicable law
    assert j["advice"]["law"] == "IPC" and j["advice"]["level"] == "warning"


def test_rejects_bad_files():
    assert upload("old.doc", b"x").status_code == 422
    assert upload("empty.txt", b"   ").status_code == 422
    assert upload("big.pdf", b"%PDF-" + b"0" * (documents.MAX_BYTES + 10)).status_code == 422


def test_text_file_after_reform():
    j = upload("note.txt", "Incident on 3 August 2024. Booked under Section 379 IPC.".encode()).json()
    assert j["advice"]["law"] == "BNS"
    assert j["citations"]["citations"][0]["suggestion"].startswith("under Section 303(2) BNS")


def test_uploaded_fir_counts_as_registered():
    j = upload("fir_sample.pdf").json()
    assert j["inferred"]["police_status"] == "Yes, FIR registered"


def test_scan_without_server_ocr_asks_browser(monkeypatch):
    monkeypatch.setattr(documents, "_ocr_langs", lambda: None)
    r = upload("fir_scan.png")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "needs_ocr"


def test_browser_ocr_text_endpoint():
    text = (FIX / "fir_sample.docx").exists() and "Date of occurrence: 14/02/2024. Booked u/s 420/34 IPC. Also s. 498-A I.P.C."
    j = c.post("/api/document-text", json={"text": text, "filename": "scan.jpg", "lang": "hi"}).json()
    assert j["document"]["kind"] == "browser-ocr" and j["advice"]["law"] == "IPC"
    assert "IPC" in j["advice"]["message"] and "धारा" in j["advice"]["message"]  # Hindi advice
    assert any(x["suggestion"] == "u/s 318(4)/3(5) BNS" for x in j["citations"]["citations"])


def test_rate_limit(monkeypatch):
    from app import main
    monkeypatch.setitem(main.LIMITS, "doc", 2)
    main._hits.clear()
    codes = [c.post("/api/document-text", json={"text": "Booked under Section 379 IPC on 3 August 2024 in Pune."}).status_code for _ in range(3)]
    assert codes[:2] == [200, 200] and codes[2] == 429
    main._hits.clear()


def test_ocr_fixups_and_check_note():
    j = c.post("/api/document-text", json={"text": "घटना की तारीख: 4/02/2024\nघारा 420/34 TPC के तहत मामला दर्ज", "lang": "hi"}).json()
    assert any(x["suggestion"] == "u/s 318(4)/3(5) BNS" or "318(4)" in (x["suggestion"] or "") for x in j["citations"]["citations"])
    assert "2024-02-04" in j["advice"]["ocr_check"]
