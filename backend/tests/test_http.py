"""HTTP-level checks of the orchestrator API."""
import pytest
from fastapi.testclient import TestClient

from app import lc_client
from app.main import app

c = TestClient(app)


def test_status():
    r = c.get("/api/status").json()
    assert r["offence_types"] > 20 and "classifier" in r


def test_rejects_empty_narrative():
    assert c.post("/api/analyze", json={"narrative": "hi"}).status_code == 422


@pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")
def test_analyze_roundtrip():
    r = c.post("/api/analyze", json={"narrative": "Someone stole my laptop from my house on 10 October 2024 in Mumbai.",
                                     "answers": {"police_status": "Not yet"}, "finalize": True}).json()
    assert r["ready"] and r["regime"]["law"] == "BNS"
    assert any(s["ipc"] == "380" for s in r["sections"])
    assert "LegalCompass" in r["summary"]


@pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")
def test_lookup_converter():
    assert c.get("/api/lookup", params={"q": "420"}).json()["results"][0]["new"] == "BNS 318(4)"
    r = c.get("/api/lookup", params={"q": "CrPC 154"}).json()
    assert r["code"] == "CrPC" and r["results"][0]["new"] == "BNSS 173"
    assert any(x["old"] == "IPC 302" for x in c.get("/api/lookup", params={"q": "bns 103(1)"}).json()["results"])
    assert c.get("/api/lookup", params={"q": "hello"}).status_code == 422


@pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")
def test_date_checker_and_editable_facts():
    assert c.get("/api/applicable-law", params={"date": "2024-06-30"}).json()["law"] == "IPC"
    assert c.get("/api/applicable-law", params={"date": "2024-07-01"}).json()["law"] == "BNS"
    r = c.post("/api/analyze", json={"narrative": "On 12 March 2025 in Pune I lost Rs 45,000 through a fake UPI call."}).json()
    assert {"offence_date", "state"} <= {q["id"] for q in r["inferred_questions"]}
    # a corrected fact overrides what was read from the text
    r2 = c.post("/api/analyze", json={"narrative": "On 12 March 2025 in Pune I lost Rs 45,000 through a fake UPI call.",
                                      "answers": {"offence_date": "2024-03-12"}, "finalize": True}).json()
    assert r2["regime"]["law"] == "IPC"
