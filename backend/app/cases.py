"""Optional similar-case retrieval over a local index built from IL-TUR (see scripts/build_case_index.py).

The index stays on your machine (IL-TUR licence: research use, no redistribution).
Ranking: judgments that share at least one predicted IPC section are preferred (case-type filter), then ordered
by text similarity to the user's description; label overlap only breaks near-ties. The snippet shown is the
passage of the judgment that best matches the description, not its first lines. IL-TUR does not carry court or
date metadata for every document, so jurisdiction and recency filters are not offered yet.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np

from . import config

MIN_SIM = 0.03
STOP = set("""a an the of to in and or for by with on as at is are was were be been has have had it its this that
these those from his her their my our me i he she they we you him them not no but if so than then there which who
whom what when where while into over under after before about also any all can could would should may might shall
through upon did does done got get one some very being own out off just only same such per via viz""".split())
# IL-TUR removes names, section numbers and Act names; say it in plain words instead of showing tags
MASKS = [(re.compile(r"(?:<ENTITY>\s*)+(?:[SDWC]/[Oo]\.?\s*(?:<ENTITY>\s*)+)?"), "a person "),
         (re.compile(r"(?:under\s+)?(?:<SECTION>\s*(?:,|and|r/w|read with|/)?\s*)+(?:of\s+(?:the\s+)?<ACT>)?", re.I), "under the relevant law "),
         (re.compile(r"<ACT>"), "the Act"), (re.compile(r"\s+([,.;:])"), r"\1"), (re.compile(r"\s{2,}"), " ")]
# court paperwork that says nothing about the facts
JUNK = re.compile(r"signature not verified|digitally signed|signing date|page \d+ of \d+|bail appl|crm[- ]?(?:m[- ]?)?no|"
                  r"crl\.?\s*(?:a|m\.?p|rev)|w\.?p\.?\s*\(|\bversus\b|\bvs\.?\b|for the (?:petitioner|respondent|state|appellant)|"
                  r"\badvocate\b|\bcounsel\b|hon'?ble|coram|j\s*u\s*d\s*g\s*m\s*e\s*n\s*t|\bo\s*r\s*d\s*e\s*r\b|"
                  r"reserved on|pronounced on|date of decision|status reports? dated|learned app|notice (?:of the application )?was issued|"
                  r"\bin re\b|@|\.{3,}", re.I)
# a sentence that states what the court decided, when the stored text contains one
OUTCOME = re.compile(r"\b(convicted|acquitted|conviction|acquittal|sentenced|bail\s+(?:is\s+|was\s+|stands\s+)?(?:granted|rejected|refused|dismissed|allowed)|"
                     r"(?:appeal|petition|application|revision)\s+(?:is\s+|was\s+|stands\s+|are\s+)?(?:allowed|dismissed|rejected|disposed)|quashed|discharged|set\s+aside)\b", re.I)
_DUP_LAW = re.compile(r"under the relevant law(?:\s*(?:read with|r/w|and|,)\s*(?:under\s+)?the relevant law)+")
_ABBR = re.compile(r"\b(Rs|No|Nos|viz|Mr|Mrs|Ms|Dr|Sh|Smt|Sri|Shri|vs|Sec|Ex|Cr|Crl|Art|St|Ltd|Co|i\.e|e\.g|S/o|D/o|W/o)\.\s+", re.I)
_SENT = re.compile(r"(?<=[.;:?!])\s+(?=[A-Z0-9(\"'])")


@lru_cache(maxsize=1)
def load():
    if not config.CASE_INDEX_PATH.exists():
        return None
    import warnings

    import joblib
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return joblib.load(config.CASE_INDEX_PATH)


def available() -> bool:
    return config.CASE_INDEX_PATH.exists()


def _clean(t: str) -> str:
    for rx, rep in MASKS:
        t = rx.sub(rep, t)
    return _DUP_LAW.sub("under the relevant law", t).strip()


def _stem(w: str) -> str:
    for suf in ("ings", "ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _terms(t: str) -> set[str]:
    words = {_stem(w) for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 2 and w not in STOP and w not in GENERIC}
    nums = {n.replace(",", "") for n in re.findall(r"\d[\d,]{2,}", t)}  # amounts like 45,000
    return words | nums


# words that appear in almost every judgment and say nothing about similarity
GENERIC = set("""case court accused complainant petitioner respondent appellant state police person section act
learned said present further filed alleged allegation offence offences punishable trial judge order judgment""".split())


def _sentences(text: str) -> list[str]:
    out = []
    for s in _SENT.split(_ABBR.sub(lambda m: m.group(0).rstrip() + "\x00", _clean(text))):
        s = s.replace("\x00", " ").strip(" .")
        if len(s.split()) >= 8 and not JUNK.search(s) and sum(c.isdigit() for c in s) < len(s) * 0.25:
            out.append(s + ".")
    return out


def best_passage(text: str, query: str, max_words: int = 75) -> tuple[str, list[str]]:
    """The run of 1-3 fact sentences that shares the most words with the description, and the words it shares."""
    sents = _sentences(text) or [_clean(text)]
    q = _terms(query)
    best, best_score = sents[0], -1.0
    for i in range(len(sents)):
        for n in (1, 2, 3):
            chunk = " ".join(sents[i:i + n])
            if n > 1 and (i + n > len(sents) or len(chunk.split()) > max_words):
                break
            # most shared words wins; among equals prefer a passage with enough substance (about 40 words)
            score = len(q & _terms(chunk)) + 0.002 * min(len(chunk.split()), 40) - 0.004 * max(0, len(chunk.split()) - 40)
            if score > best_score:
                best, best_score = chunk, score
    words = best.split()
    if len(words) > max_words:
        best = " ".join(words[:max_words]) + " …"
    shared = q & _terms(best)
    # report the user's own words (not stems) so the website can highlight them in the passage
    shown, seen = [], set()
    for w in re.findall(r"\d[\d,]{2,}|[A-Za-z]+", query):
        key = w.replace(",", "") if w[0].isdigit() else _stem(w.lower())
        if key in shared and key not in seen:
            seen.add(key)
            shown.append(w)
    return best, shown[:8]


def outcome_sentence(text: str, passage: str) -> str | None:
    """The last sentence of the stored text that states a decision (conviction, acquittal, bail...), if any."""
    hits = [x for x in _sentences(text) if OUTCOME.search(x) and x.rstrip(".") not in passage]
    return hits[-1] if hits else None


def similar(text: str, ipc_sections: list[str], k: int = 5) -> dict:
    idx = load()
    if idx is None:
        return {"available": False, "results": [],
                "reason": "Similar-case index not built yet. Run scripts/build_case_index.py with your Hugging Face token."}
    sims = (idx["matrix"] @ idx["vec"].transform([text]).T).toarray().ravel()
    want = set(ipc_sections)
    if want:
        overlap = np.array([len(want & set(m["ipc"])) / len(want | set(m["ipc"])) for m in idx["meta"]])
        score = np.where(overlap > 0, sims + 0.05 * overlap, -1.0)  # same case type first, similarity decides
        if (score > MIN_SIM).sum() < k:  # too few same-type matches: fall back to text similarity alone
            score = np.maximum(score, sims - 0.5)
    else:
        score = sims
    res, seen = [], set()
    for i in score.argsort()[::-1]:
        if len(res) >= k or sims[i] < MIN_SIM:
            break
        m = idx["meta"][i]
        full = m.get("text") or m["snippet"]
        passage, matched = best_passage(full, text)
        if passage in seen:
            continue
        seen.add(passage)
        res.append({"id": m["id"], "snippet": passage, "matched_terms": matched, "outcome_text": outcome_sentence(full, passage), "ipc": m["ipc"],
                    "shared_sections": sorted(want & set(m["ipc"]), key=lambda s: (len(s), s)),
                    "similarity": round(float(sims[i]), 3),
                    "source": idx.get("source", "IL-TUR (research use only)")})
    return {"available": True, "results": res, "filters": {"case_type": sorted(want)},
            "passages": "best-matching passage" if idx["meta"] and "text" in idx["meta"][0] else "opening lines (rebuild the index for best-matching passages)"}
