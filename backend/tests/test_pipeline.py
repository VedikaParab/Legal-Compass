"""End-to-end tests of the orchestrator. Needs the LegalCompass API running on LEGALCOMPASS_API."""
import pytest

from app import lc_client, pipeline
from app.extract import extract, find_dates
from app.summary import mask

pytestmark = pytest.mark.skipif(not lc_client.health(), reason="LegalCompass API not running")


def ipcs(r):
    return [s["ipc"] for s in r["sections"]]


def test_fraud_after_reform_uses_bns_and_bnss():
    r = pipeline.analyze("On 12 March 2025 a caller pretending to be from my bank took my OTP and Rs 45,000 via UPI.",
                         {"state": "Maharashtra", "police_status": "Not yet"})
    assert r["regime"]["law"] == "BNS" and r["procedure_code"] == "BNSS"
    assert "420" in ipcs(r)
    s420 = next(s for s in r["sections"] if s["ipc"] == "420")
    assert [b["provision"] for b in s420["bns"]] == ["BNS 318(4)"]
    titles = " ".join(st["title"] for st in r["next_steps"]["steps"])
    assert "1930" in titles and "FIR" in titles
    assert "BNSS 173" in " ".join(st["detail"] for st in r["next_steps"]["steps"])


def test_offence_before_reform_uses_ipc():
    r = pipeline.analyze("My neighbour beat me with an iron rod on 5 January 2024 and I was hospitalised with a fracture.",
                         {"state": "Delhi", "police_status": "Not yet", "accused_count": "One person"}, finalize=True)
    assert r["regime"]["law"] == "IPC"
    assert "326" in ipcs(r)  # grievous hurt by dangerous weapon
    assert r["procedure_code"] == "BNSS"  # proceedings starting now follow the BNSS even for an IPC offence


def test_missing_date_abstains_and_asks():
    r = pipeline.analyze("Someone stole my phone from my bag in the train.")
    assert r["regime"]["decision"] == "abstain"
    assert r["questions"][0]["id"] == "offence_date" and r["questions"][0]["required"]
    assert "379" in ipcs(r)


def test_split_provision_returns_both_targets():
    r = pipeline.analyze("My husband and in-laws have been harassing me for dowry since 2022 and beat me.",
                         {"offence_date": "2023-05-01", "ongoing": "Over a period (still continuing or repeated)"},
                         finalize=True)
    s = next(s for s in r["sections"] if s["ipc"] == "498A")
    assert {b["provision"] for b in s["bns"]} == {"BNS 85", "BNS 86"}
    assert r["regime"]["decision"] == "needs_review"


def test_group_adds_common_intention():
    r = pipeline.analyze("Three men attacked me with sticks near my shop on 2 August 2024.", finalize=True)
    assert "34" in ipcs(r)
    s34 = next(s for s in r["sections"] if s["ipc"] == "34")
    assert s34["bns"][0]["provision"] == "BNS 3(5)"


def test_unclear_narrative():
    r = pipeline.analyze("I want to know about my rights regarding this matter please help.")
    assert not r["understood"] and r["sections"] == []


def test_date_parsing_and_masking():
    assert [d.isoformat() for d in find_dates("on 03/07/2024 and March 5, 2023")] == ["2023-03-05", "2024-07-03"]
    assert extract("I live in Pune")["inferred"]["state"] == "Maharashtra"
    m = mask("Call Mr Ramesh Kumar on 9876543210 or mail ramesh@example.com, Aadhaar 1234 5678 9012")
    assert "9876543210" not in m and "example.com" not in m and "Ramesh" not in m and "1234 5678" not in m


def test_every_rule_section_exists_in_mapping():
    from app.offences import OFFENCES
    secs = {s for o in OFFENCES for s in o.ipc}
    for o in OFFENCES:
        for table in o.refine.values():
            for v in table.values():
                secs |= set(v)
    missing = [s for s in sorted(secs) if (lc_client.lookup("IPC", s) or {}).get("status") not in ("mapped", "multiple_targets")]
    assert not missing, missing


def test_continuing_offence_since_year_needs_review():
    r = pipeline.analyze("My husband and in-laws have been harassing me for dowry since 2022 and beat me last week.",
                         {"offence_date": "2026-10-06", "state": "Maharashtra", "police_status": "Not yet"}, finalize=True)
    assert r["facts"]["ongoing_since_year"] == 2022
    assert r["regime"]["decision"] == "needs_review"


def test_best_passage_and_masks():
    from app.cases import best_passage
    text = "Item no 40 anticipatory bail application filed. " * 20 + "The husband demanded dowry and beat <ENTITY> <ENTITY> with a rod. " + "Order follows. " * 30
    p, matched = best_passage(text, "my husband beat me for dowry")
    assert "dowry" in p and "<ENTITY>" not in p and "a person" in p
    assert {"husband", "beat", "dowry"} <= set(matched)
    # court paperwork is skipped even when it shares words
    q = "the police refused bail and my husband beat me"
    p2, _ = best_passage("Signature Not Verified Digitally Signed By <ENTITY> Bail Appl. No.12/2020 Page 2 of 9 police bail. "
                         "The husband beat the complainant on 2 May. Order reserved.", q)
    assert "Signature" not in p2 and "husband beat" in p2


def test_fir_registered_asks_fir_date_and_uses_crpc_if_before_reform():
    r = pipeline.analyze("Someone stole my phone on 3 Aug 2024.", {"police_status": "Yes, FIR registered"})
    assert "fir_date" in [q["id"] for q in r["questions"]]
    r = pipeline.analyze("Someone stole my phone on 3 May 2024.",
                         {"police_status": "Yes, FIR registered", "fir_date": "2024-06-01"}, finalize=True)
    assert r["procedure_code"] == "CrPC"


def test_case_passage_cleanup_and_outcome():
    from app.cases import best_passage, outcome_sentence
    t = ("allowed debajyoti CRM No.119 of 2019 In re : Deepak Das @ Dipak Kumar Das ..... Petitioner. "
         "The complainant filed a case under <SECTION> of <ACT> read with <SECTION> and <SECTION> of the <ACT> against the petitioner who took money for goods. "
         "The petitioner failed to supply the goods and refused to refund the advance. "
         "The trial court convicted the accused and the appeal was dismissed.")
    p, _ = best_passage(t, "I paid an advance for goods and he did not refund it")
    assert "Deepak" not in p and "refund" in p
    assert "read with" not in p and p.count("relevant law") == 1
    assert "convicted" in (outcome_sentence(t, p) or p)
    short, _ = best_passage(t, "advance for goods", max_words=30)   # decision left out of a short passage...
    assert "convicted" in outcome_sentence(t, short)                 # ...is still reported separately
