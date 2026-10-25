"""Suggested next steps: fixed, reviewed templates (not free LLM text).

Procedural provisions are written once as CrPC sections and converted to BNSS through the LegalCompass mapping
when the proceedings fall under the new code, so a step always cites the code that actually governs it.
"""
from __future__ import annotations

from . import lc_client

HELPLINES = {
    "emergency": ("Emergency (police / ambulance)", "112"),
    "cyber": ("National Cyber Crime Helpline — report within hours for the best chance of freezing money", "1930 · cybercrime.gov.in"),
    "women": ("Women Helpline", "181"),
    "child": ("Childline", "1098"),
    "legal_aid": ("Free legal aid (NALSA / District Legal Services Authority)", "15100"),
}


def _proc(crpc: str, regime: str | None) -> str:
    """'CrPC 154' or its BNSS counterpart, depending on which code governs the proceedings."""
    if regime != "BNSS":
        return f"CrPC {crpc}"
    try:
        r = lc_client.lookup("CrPC", crpc)
        new = sorted({x["new"]["provision"] for x in (r or {}).get("results", [])})
        if new:
            return f"{' / '.join(new)} (formerly CrPC {crpc})"
    except lc_client.LegalCompassUnavailable:
        pass
    return f"CrPC {crpc}"


def next_steps(offence_ids: list[str], categories: set[str], answers: dict, procedure: str | None,
               serious: bool, lang: str = "en") -> dict:
    from . import i18n
    lang = i18n.lang_of(lang)
    status = answers.get("police_status", "Not yet")
    online = answers.get("online") == "Yes"
    refs = {"p154": _proc("154", procedure), "p156": _proc("156", procedure), "p200": _proc("200", procedure),
            "p357A": _proc("357A", procedure)}
    keys = []
    if serious:
        keys.append("danger")
    if online and ({"cheating", "impersonation", "extortion"} & set(offence_ids)):
        keys.append("cyber")
    keys.append({"Not yet": "fir_new", "Yes, but police refused to register an FIR": "escalate"}.get(status, "fir_existing"))
    if "body" in categories or answers.get("injury", "").startswith(("Simple", "Serious")):
        keys.append("medical")
    if "women" in categories:
        keys.append("women")
    keys += ["evidence", "legal_aid"]
    steps = [i18n.step(k, lang, show_zero=(k == "fir_new" and procedure == "BNSS"), **refs) for k in keys]

    lines = ["emergency", "legal_aid"]
    if online:
        lines.insert(1, "cyber")
    if "women" in categories:
        lines.insert(1, "women")
    if "kidnapping" in offence_ids:
        lines.insert(1, "child")
    return {"steps": steps, "helplines": [{"key": k, "name": i18n.helpline(k, lang), "contact": HELPLINES[k][1]} for k in lines]}
