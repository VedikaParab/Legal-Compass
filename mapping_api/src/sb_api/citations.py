"""Find statute citations in free text (FIRs, charge-sheets, judgments, notes) and convert them.

Handles the forms Indian practitioners actually write:
  "u/s 420/34 IPC", "Sections 467, 468 and 471 of the Indian Penal Code", "s. 498-A I.P.C.",
  "IPC 302", "Section 154 Cr.P.C.", "Sec. 65B of the Evidence Act", "302 r/w 34 IPC", "BNS 103(1)".
"""
from __future__ import annotations

import re

from sb.corpus import get

from .store import OLD_TO_NEW, NEW_TO_OLD, get_store

CODE_PATTERNS = [
    ("CrPC", r"Cr\.\s?P\.\s?C\.|Cr\.?P\.?C\b|Code\s+of\s+Criminal\s+Procedure(?:,?\s*1973)?"),
    ("IPC", r"I\.\s?P\.\s?C\.|IPC\b|Indian\s+Penal\s+Code(?:,?\s*1860)?"),
    ("IEA", r"I\.\s?E\.\s?A\.|IEA\b|(?:Indian\s+)?Evidence\s+Act(?:,?\s*1872)?"),
    ("BNSS", r"B\.\s?N\.\s?S\.\s?S\.|BNSS\b|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:,?\s*2023)?"),
    ("BNS", r"B\.\s?N\.\s?S\.|BNS\b|Bharatiya\s+Nyaya\s+Sanhita(?:,?\s*2023)?"),
    ("BSA", r"B\.\s?S\.\s?A\.|BSA\b|Bharatiya\s+Sakshya\s+Adhiniyam(?:,?\s*2023)?"),
]
CODE_RE = "|".join(f"(?P<{c}>{p})" for c, p in CODE_PATTERNS)
NUM = r"\d{1,3}(?!\d)(?:\s?-?\s?(?-i:[A-Z]{1,2})(?![A-Za-z/]))?(?:\s?\(\w{1,4}\))*"
SEP = r"\s*(?:/|,|&|\band\b|\br/w\b|\bread\s+with\b|\bwith\b)\s*"
LIST = rf"{NUM}(?:{SEP}{NUM})*"
LEAD = r"(?P<under>u/s\.?\s*|under\s+)?(?:sections?\b|secs?\.?|ss?\.|§)?\s*"
PRE = re.compile(rf"(?:{LEAD})?(?P<nums>{LIST})\s*,?\s*(?:of\s+(?:the\s+)?)?(?:{CODE_RE})(?![A-Za-z])", re.I)
POST = re.compile(rf"(?<![A-Za-z])(?:{CODE_RE})\s*,?\s*(?:{LEAD})?(?P<nums>{LIST})", re.I)


def _code_of(m) -> str:
    for c, _ in CODE_PATTERNS:
        if m.group(c):
            return c
    raise AssertionError


def _numbers(s: str) -> list[str]:
    return [re.sub(r"[\s-]", "", x).upper() for x in re.findall(NUM, s, re.I)]


def find_citations(text: str) -> list[dict]:
    """Return citations as [{start, end, text, code, sections}] (non-overlapping, in order)."""
    found, taken = [], []
    for rx in (PRE, POST):
        for m in rx.finditer(text):
            s, e = m.span()
            s += len(text[s:e]) - len(text[s:e].lstrip())
            if any(s < te and e > ts for ts, te in taken):
                continue
            code = _code_of(m)
            secs = [x for x in _numbers(m.group("nums")) if get(code, re.match(r"\d+[A-Z]*", x).group(0))]
            if not secs:
                continue
            taken.append((s, e))
            under = (m.group("under") or "").strip()
            found.append({"start": s, "end": e, "text": text[s:e], "code": code, "sections": secs, "lead": under})
    return sorted(found, key=lambda x: x["start"])


def convert_citation(code: str, sections: list[str], lead: str = "") -> dict:
    st = get_store()
    target = OLD_TO_NEW.get(code) or NEW_TO_OLD[code]
    items, ambiguous = [], False
    for sec in sections:
        res = st.lookup(code, sec)
        side = "new" if code in OLD_TO_NEW else "old"
        targets = sorted({r[side]["provision"] or "NEW" for r in res["results"]})
        ambiguous |= res["status"] != "mapped"
        items.append({"section": sec, "status": res["status"], "targets": targets,
                      "substantive_change": sorted({r["substantive_change"] for r in res["results"]}),
                      "notes": [r["notes"] for r in res["results"] if r["notes"]][:3],
                      "row_ids": [r["row_id"] for r in res["results"]]})
    suggestion = None
    if not ambiguous:
        nums = [re.sub(rf"^{target}\s*", "", it["targets"][0]) for it in items]
        plural = f"Section{'s' if len(nums) > 1 else ''} {', '.join(nums)} {target}"
        if lead.lower().startswith("u/s"):
            suggestion = f"u/s {'/'.join(nums)} {target}"
        elif lead:
            suggestion = f"{lead} {plural}"
        else:
            suggestion = plural
    return {"code": code, "target_code": target, "items": items, "ambiguous": ambiguous, "suggestion": suggestion}


def convert_text(text: str, annotate_original: bool = True) -> dict:
    """Replace every unambiguous citation; leave ambiguous ones in place and list them for the user to resolve."""
    cits = find_citations(text)
    out, pos, conversions = [], 0, []
    for c in cits:
        conv = convert_citation(c["code"], c["sections"], c["lead"])
        conversions.append({**c, **conv})
        out.append(text[pos:c["start"]])
        if conv["suggestion"]:
            rep = conv["suggestion"] + (f" (formerly {c['text'].strip()})" if annotate_original else "")
            nxt = text[c["end"]:c["end"] + 1]
            if c["text"].endswith(".") and (nxt == "" or nxt.isspace()) and not rep.endswith("."):
                rep += "."  # keep the sentence full stop swallowed by a dotted abbreviation like "Cr.P.C."
            out.append(rep)
        else:
            out.append(c["text"])
        pos = c["end"]
    out.append(text[pos:])
    return {"converted_text": "".join(out), "citations": conversions,
            "needs_attention": [x for x in conversions if x["ambiguous"]]}
