"""Shareable case summary with personal identifiers masked."""
from __future__ import annotations

import re

MASKS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[email]"),
    (re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[phone]"),
    (re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"), "[ID number]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    (re.compile(r"(?<!\d)\d{9,18}(?!\d)"), "[account number]"),
    (re.compile(r"\b[\w.-]+@(?:ok\w+|upi|ybl|paytm|ibl|axl|apl)\b", re.I), "[UPI ID]"),
    (re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Shri|Smt)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"), "[name]"),
]


def mask(text: str) -> str:
    for rx, rep in MASKS:
        text = rx.sub(rep, text)
    return text


def build(narrative: str, answers: dict, regime: dict, sections: list[dict], steps: list[dict]) -> str:
    law = regime.get("law") or "to be decided (incident date needed)"
    lines = ["CASE SUMMARY (prepared with LegalCompass — for discussion with a lawyer, not legal advice)", ""]
    lines.append("What happened (personal details masked):")
    lines.append(mask(narrative.strip()))
    lines.append("")
    facts = [("Incident date", answers.get("offence_date")), ("State", answers.get("state")),
             ("Police status", answers.get("police_status")), ("Amount involved", answers.get("amount")),
             ("Injury", answers.get("injury")), ("People involved", answers.get("accused_count"))]
    lines.append("Key facts:")
    lines += [f"- {k}: {v}" for k, v in facts if v]
    lines.append("")
    lines.append(f"Applicable penal code: {law}")
    if regime.get("reason"):
        lines.append(f"  ({regime['reason']})")
    lines.append("")
    lines.append("Possibly applicable sections (to be confirmed by a lawyer):")
    for s in sections:
        bns = ", ".join(t["provision"] for t in s["bns"]) or "no BNS counterpart in the mapping"
        lines.append(f"- IPC {s['ipc']} ({s['ipc_heading']})  <->  {bns}  — {s['offence']}")
    lines.append("")
    lines.append("Suggested next steps:")
    lines += [f"- {st['title']}" for st in steps]
    return "\n".join(lines)
