"""Which law applies? A transparent, rule-based helper (the "Constitutional Temporal Router" of the paper).

Rules (to be confirmed by the project's law reviewer before public launch):
  * Substantive offence law follows the date of the offence (Art. 20(1) Constitution; BNS s. 358):
      offence before 1 July 2024 -> IPC;  on/after -> BNS.  Offence spanning the date -> needs review.
  * Procedure follows the proceedings (BNSS s. 531(2)): an appeal, application, trial, inquiry or investigation
      pending immediately before 1 July 2024 continues under the CrPC; proceedings begun on/after -> BNSS.
  * Evidence follows the same saving rule (BSA s. 170(2)): pending proceedings -> IEA; otherwise -> BSA.
  * Missing dates -> the helper abstains for that domain instead of guessing.
"""
from __future__ import annotations

from datetime import date

T_STAR = date(2024, 7, 1)
DISCLAIMER = ("Rule-based guidance, not legal advice. Transitional questions (continuing offences, beneficial "
              "changes in punishment, stage of proceedings) can turn on facts; confirm with counsel.")


def _regime(d: date | None, before: str, after: str) -> str | None:
    if d is None:
        return None
    return before if d < T_STAR else after


def applicable_law(offence_date: date | None = None, offence_end_date: date | None = None,
                   proceedings_start_date: date | None = None) -> dict:
    out = {"commencement_date": T_STAR.isoformat(), "inputs": {
        "offence_date": offence_date and offence_date.isoformat(),
        "offence_end_date": offence_end_date and offence_end_date.isoformat(),
        "proceedings_start_date": proceedings_start_date and proceedings_start_date.isoformat()}}

    # substantive
    if offence_date is None:
        sub = {"decision": "abstain", "law": None,
               "reason": "Offence date not given. The applicable penal law depends on when the offence was committed."}
    elif offence_end_date and offence_date < T_STAR <= offence_end_date:
        sub = {"decision": "needs_review", "law": "IPC and/or BNS",
               "reason": "The offence period spans 1 July 2024 (continuing offence). Acts before the date fall under "
                         "the IPC and acts on/after under the BNS; take advice."}
    else:
        law = _regime(offence_date, "IPC", "BNS")
        sub = {"decision": "decided", "law": law,
               "reason": f"Offence committed {'before' if law == 'IPC' else 'on or after'} 1 July 2024.",
               "basis": ["Constitution of India, Art. 20(1)", "BNS s. 358"]}

    # procedure + evidence
    if proceedings_start_date is None:
        proc = {"decision": "abstain", "law": None,
                "reason": "Date proceedings began (FIR / complaint / investigation) not given."}
        evid = dict(proc)
    else:
        p = _regime(proceedings_start_date, "CrPC", "BNSS")
        proc = {"decision": "decided", "law": p, "basis": ["BNSS s. 531(2)"],
                "reason": ("Proceedings pending before 1 July 2024 continue under the CrPC." if p == "CrPC"
                           else "Proceedings begun on or after 1 July 2024 follow the BNSS, even for an older offence.")}
        e = "IEA" if p == "CrPC" else "BSA"
        evid = {"decision": "decided", "law": e, "basis": ["BSA s. 170(2)"],
                "reason": ("Pending proceedings continue under the Indian Evidence Act." if e == "IEA"
                           else "The Bharatiya Sakshya Adhiniyam applies.")}
    if offence_date and proceedings_start_date and proceedings_start_date < offence_date:
        out["warning"] = "Proceedings start date is earlier than the offence date - please check the dates."
    out.update({"substantive": sub, "procedure": proc, "evidence": evid, "disclaimer": DISCLAIMER,
                "verification_status": "pending law-reviewer confirmation"})
    return out
