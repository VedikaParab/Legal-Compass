"""Hindi / Marathi understanding and translated output."""
import pytest

from app import lc_client, pipeline
from app.extract import extract

pytestmark = pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")


def ipcs(r):
    return [s["ipc"] for s in r["sections"]]


def test_hindi_dowry_continuing():
    r = pipeline.analyze("मेरे पति और ससुराल वाले 2022 से दहेज के लिए परेशान कर रहे हैं और पिछले हफ्ते मुझे लाठी से मारा, हड्डी टूट गई।", {}, True, "hi")
    assert {"326", "498A"} <= set(ipcs(r))
    assert r["regime"]["decision"] == "needs_review" and "IPC" in r["regime"]["reason"]
    assert r["next_steps"]["steps"][0]["title"].startswith("अगर") or any("एफआईआर" in s["title"] for s in r["next_steps"]["steps"])


def test_marathi_fraud_with_devanagari_digits():
    r = pipeline.analyze("१५ मार्च २०२५ रोजी पुण्यात एका व्यक्तीने बँकेचा अधिकारी असल्याचे सांगून ओटीपी घेतला आणि माझी ४५,००० रुपयांची फसवणूक केली.",
                         {"police_status": "Not yet"}, True, "mr")
    assert r["regime"]["law"] == "BNS" and "420" in ipcs(r)
    assert r["answers"]["state"] == "Maharashtra" and r["answers"]["amount"] == "₹45,000"
    assert any("1930" in s["title"] for s in r["next_steps"]["steps"])
    assert "एफआयआर" in " ".join(s["title"] for s in r["next_steps"]["steps"])


def test_questions_translated_but_values_english():
    r = pipeline.analyze("Someone stole my phone.", {}, False, "hi")
    q = next(q for q in r["questions"] if q["id"] == "police_status")
    assert q["text"].startswith("क्या") and q["options"][0] == "Not yet" and q["option_labels"][0] == "अभी नहीं"


def test_amount_number_before_word():
    assert extract("I lost 45,000 rupees")["inferred"]["amount"] == "₹45,000"
