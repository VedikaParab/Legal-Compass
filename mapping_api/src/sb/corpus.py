"""Statute corpus: load section texts for the six codes and extract sub-provisions.

Sources (see data/README.md):
  * IPC / CrPC / IEA text: civictech-India/Indian-Law-Penal-Code-Json
  * BNS / BNSS / BSA text: GSMS-B indian-legal-sections-bns-bnss-bsa-2023
  both as normalised in gsms-b/indian-legal-mcp (data/sections.json, MIT).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "statutes_sections.json"

ACT_ALIASES = {"CrPC": "CRPC", "CRPC": "CRPC", "IPC": "IPC", "IEA": "IEA", "BNS": "BNS", "BNSS": "BNSS", "BSA": "BSA"}
PAIRS = {"IPC_to_BNS": ("IPC", "BNS"), "CrPC_to_BNSS": ("CrPC", "BNSS"), "IEA_to_BSA": ("IEA", "BSA")}
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}


@dataclass
class Section:
    code: str
    number: str
    title: str
    text: str
    chapter: str = ""
    segments: dict = field(default_factory=dict)  # "(1)(a)" -> text  (new codes only)

    @property
    def sid(self) -> str:
        return f"{self.code} {self.number}"

    def full(self, max_chars: int | None = None) -> str:
        t = f"Section {self.number}. {self.title}. {self.text}"
        return t if max_chars is None else t[:max_chars]


def _clean_text(code: str, number: str, title: str, text: str) -> str:
    t = text.replace("\t", " ")
    # BNS/BNSS/BSA text starts with "[Context: ...]\n\n<num>. <title>.--"
    t = re.sub(r"^\[Context:.*?\]\s*", "", t, flags=re.S)
    t = re.sub(rf"^{re.escape(number)}\.\s*", "", t)
    t = re.sub(r"[  ]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


_MARK = re.compile(r"^\s*\(([0-9]+|[a-z]{1,3})\)\s*")


def segment(text: str) -> dict:
    """Split a new-code section into sub-provisions keyed '(1)', '(1)(a)', '(a)'.

    Works on line starts. Roman numerals are treated as sub-items of the current
    clause unless they continue the letter sequence (h -> i).
    """
    segs: dict[str, list[str]] = {}
    sub, cl = None, None
    # first line may contain "Title.--(1) ..." : expose the marker
    text = re.sub(r"[—–-]{1,2}\s*\((1|a)\)", lambda m: "\n(" + m.group(1) + ")", text, count=1)
    for line in text.split("\n"):
        m = _MARK.match(line)
        if m:
            tok = m.group(1)
            if tok.isdigit():
                sub, cl = tok, None
            elif tok in ROMAN and cl is not None and not (len(tok) == 1 and cl and ord(tok) == ord(cl[-1]) + 1):
                pass  # roman sub-item: stays inside current clause
            else:
                cl = tok
        key = "".join(f"({x})" for x in (sub, cl) if x)
        if key:
            segs.setdefault(key, []).append(line.strip())
            if cl and sub:  # also accumulate into parent subsection
                segs.setdefault(f"({sub})", []).append(line.strip()) if key != f"({sub})" else None
    return {k: " ".join(v) for k, v in segs.items()}


@lru_cache(maxsize=1)
def load_corpus() -> dict[str, dict[str, Section]]:
    rows = json.loads(RAW.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Section]] = {}
    for r in rows:
        code = r["act_code"]
        if code not in {"IPC", "CRPC", "IEA", "BNS", "BNSS", "BSA"}:
            continue
        num = str(r["section_number"]).strip()
        title = (r.get("section_title") or "").strip().rstrip(".")
        text = _clean_text(code, num, title, r.get("text") or "")
        s = Section(code=code, number=num, title=title, text=text, chapter=str(r.get("chapter_title") or ""))
        if code in {"BNS", "BNSS", "BSA"}:
            s.segments = segment(text)
        out.setdefault(code, {})[num] = s
    return out


def get(code: str, number) -> Section | None:
    if number is None:
        return None
    return load_corpus().get(ACT_ALIASES[code], {}).get(str(number).strip())


def _term(heading: str | None) -> str | None:
    if not heading:
        return None
    m = re.search(r"[\"“”']([^\"“”']{2,60})[\"“”']", heading)
    return (m.group(1) if m else heading).strip(" .").lower() or None


def provision_text(code: str, section, subsection, heading=None) -> tuple[str | None, str]:
    """Return (text, how) for a provision. `how` in {'segment','term','para','section','missing'}."""
    s = get(code, section)
    if s is None:
        return None, "missing"
    if not subsection:
        return s.full(), "section"
    sub = str(subsection)
    if s.segments:
        if sub in s.segments:
            return f"Section {s.number}{sub}. {s.title}. {s.segments[sub]}", "segment"
        # '(c)' may live under '(1)'
        for k, v in s.segments.items():
            if k.endswith(sub) and k.count("(") == 2:
                return f"Section {s.number}{k}. {s.title}. {v}", "segment"
    lines = [l.strip() for l in s.text.split("\n") if l.strip()]
    m = re.fullmatch(r"para (\d+)", sub)
    term = _term(heading)
    if term:
        for l in lines:
            if term in l.lower()[: max(80, len(term) + 20)]:
                return f"Section {s.number} ({sub}). {s.title}. {l}", "term"
    if m and int(m.group(1)) < len(lines):
        return f"Section {s.number} ({sub}). {s.title}. {lines[int(m.group(1))]}", "para"
    return s.full(), "section"
