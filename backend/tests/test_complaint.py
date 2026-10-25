"""Complaint drafts (.docx)."""
import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app import lc_client
from app.main import app

c = TestClient(app)
pytestmark = pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")
FRAUD = "On 12 March 2025 a caller pretending to be from my bank took my OTP and Rs 45,000 via UPI."


def text_of(resp):
    return "\n".join(p.text for p in Document(io.BytesIO(resp.content)).paragraphs)


@pytest.mark.parametrize("kind", ["fir", "sp", "magistrate"])
def test_drafts_build(kind):
    r = c.post("/api/complaint", json={"narrative": FRAUD, "answers": {"state": "Maharashtra"}, "kind": kind})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxml")
    t = text_of(r)
    assert "BNS 318(4) (formerly IPC 420)" in t and "[Your full name]" in t and FRAUD in t
    assert "Bharatiya Nagarik Suraksha Sanhita" in t  # proceedings starting now follow the BNSS
    if kind == "fir":
        assert "Section 173 of the Bharatiya Nagarik Suraksha Sanhita" in t
    if kind == "magistrate":
        assert "Section 175 of the Bharatiya Nagarik Suraksha Sanhita" in t and "affidavit" in t


def test_pre_reform_offence_cites_ipc():
    r = c.post("/api/complaint", json={"narrative": "My neighbour hit me with an iron rod on 5 January 2024 and broke my arm.",
                                       "answers": {}, "kind": "fir"})
    t = text_of(r)
    assert "IPC 326" in t and "formerly IPC" not in t
