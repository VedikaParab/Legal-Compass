"""The orchestrator: narrative + answers -> questions and analysis.

  1. extract facts (rules, optional LLM wording later)
  2. identify likely offences (offence rules + optional IL-TUR classifier)
  3. decide which questions still matter
  4. decide the applicable code by date (LegalCompass temporal rule)
  5. map every IPC section to its BNS counterpart (LegalCompass mapping)
  6. similar cases, next steps, summary
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from . import actions, cases, classifier, extract, i18n, lc_client, llm, summary
from .offences import BY_ID, QUESTIONS, match_offences, sections_for

T_STAR = date(2024, 7, 1)
GLOBAL_QUESTIONS = ["offence_date", "police_status", "state"]
MAX_QUESTIONS = 6
DISCLAIMER = ("LegalCompass gives general legal information to help you understand your situation and find help. "
              "It is not legal advice and can be wrong — confirm with a lawyer or a Legal Services Authority before acting.")


def _parse_date(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _questions(offence_ids: list[str], answers: dict, lang: str = "en") -> list[dict]:
    order = list(GLOBAL_QUESTIONS)
    for oid in offence_ids:
        for q in BY_ID[oid].questions:
            if q not in order:
                order.append(q)
    if "Yes, FIR registered" == answers.get("police_status") and "fir_date" not in order:
        order.insert(2, "fir_date")
    d = _parse_date(answers.get("offence_date"))
    if d and d < T_STAR and "ongoing" not in order:
        order.insert(1, "ongoing")
    out = []
    for qid in order:
        q = QUESTIONS[qid]
        if answers.get(qid) not in (None, ""):
            continue
        out.append({"id": q.id, "kind": q.kind, "options": q.options, "required": q.required,
                    **i18n.question(q.id, lang, q.text, q.why, q.options)})
    return out[:MAX_QUESTIONS]


def _regime(answers: dict, since_year: int | None = None) -> tuple[dict, str | None]:
    """Penal regime (IPC/BNS/abstain/needs_review) and the procedural code for next steps."""
    od = _parse_date(answers.get("offence_date"))
    ongoing = answers.get("ongoing", "").startswith("Over a period")
    end = date.today() if ongoing else None
    if ongoing and since_year:
        start = date(since_year, 1, 1)
        if od is None or start < od:
            end = max(od or start, end or start)
            od = start  # a continuing offence starts when the conduct began, not at the latest incident
    if answers.get("police_status") == "Yes, FIR registered":
        proc_start = _parse_date(answers.get("fir_date"))
    else:
        proc_start = date.today()  # proceedings would begin now
    try:
        r = lc_client.applicable_law(od, end, proc_start)
    except lc_client.LegalCompassUnavailable as e:
        return {"decision": "unavailable", "law": None, "reason": str(e)}, None
    sub = dict(r["substantive"])
    if sub.get("decision") == "needs_review":
        sub["reason"] = ("This conduct continued across 1 July 2024. Acts before that date fall under the IPC and acts "
                         "on or after it under the BNS — a lawyer should confirm which applies to each act.")
    return sub, (r["procedure"] or {}).get("law")


def _map_ipc(ipc: str) -> dict:
    r = lc_client.lookup("IPC", ipc) or {}
    res = r.get("results", [])
    seen, bns = set(), []
    for x in res:
        p = x["new"]["provision"]
        if p in seen:
            continue
        seen.add(p)
        bns.append({"provision": p, "heading": x["new"].get("heading")})
    first = res[0] if res else {}
    return {
        "ipc": ipc,
        "ipc_heading": (first.get("old") or {}).get("heading") or "",
        "bns": bns,
        "status": r.get("status", "unknown"),
        "mapping_explained": first.get("mapping_type_explained", ""),
        "change": first.get("substantive_change"),
        "change_explained": first.get("substantive_change_explained", ""),
        "notes": sorted({x["notes"] for x in res if x.get("notes")})[:2],
        "row_ids": [x["row_id"] for x in res],
        "source": first.get("source"),
    }


def analyze(narrative: str, answers: dict | None = None, finalize: bool = False, lang: str = "en") -> dict:
    lang = i18n.lang_of(lang)
    narrative = (narrative or "").strip()
    user_answers = {k: v for k, v in (answers or {}).items() if v not in (None, "")}
    ex = extract.extract(narrative)
    merged = {**ex["inferred"], **user_answers}

    rules_text = narrative
    if ex["facts"].get("script") == "devanagari" and llm.enabled():
        en = llm.translate_to_english(summary.mask(narrative))  # optional: widens rule coverage for free-form Hindi/Marathi
        if en:
            rules_text = f"{narrative}\n{en}"
            ex["facts"]["machine_translation"] = en
    matched = match_offences(rules_text)
    clf = classifier.predict(narrative) if classifier.available() else []
    offence_ids = [m["id"] for m in matched]

    questions = _questions(offence_ids, merged, lang)
    required_missing = [q["id"] for q in questions if q["required"]]
    ready = finalize or not questions

    regime, procedure = _regime(merged, ex["facts"].get("ongoing_since_year"))

    # sections: offence rules first, then classifier suggestions not already covered
    sections, used = [], set()
    for m in matched:
        o = BY_ID[m["id"]]
        for ipc in sections_for(o.id, merged):
            if ipc in used:
                continue
            used.add(ipc)
            sections.append({**_map_ipc(ipc), "offence": i18n.offence(o.id, lang, o.label), "offence_id": o.id, "basis": "offence rules",
                             "evidence": m["evidence"], "confidence": round(m["score"], 2)})
    if merged.get("accused_count") in ("Two to four people", "Five or more people") and sections and "34" not in used:
        used.add("34")
        sections.append({**_map_ipc("34"), "offence": i18n.offence("_common_intention", lang, "Acts done by several persons together (add-on)"), "offence_id": "common_intention",
                         "basis": "follow-up answer", "evidence": [merged["accused_count"]], "confidence": 0.6})
    for c in clf:
        if c["above_threshold"] and c["ipc"] not in used and len(used) < 8:
            used.add(c["ipc"])
            sections.append({**_map_ipc(c["ipc"]), "offence": i18n.offence("_classifier", lang, "Suggested by the IL-TUR statute classifier"), "offence_id": "classifier",
                             "basis": "classifier", "evidence": [], "confidence": round(c["prob"], 2)})

    law = regime.get("law")
    primary = "BNS" if law == "BNS" else ("IPC" if law == "IPC" else "both")
    categories = {BY_ID[i].category for i in offence_ids}
    serious = any(BY_ID[i].serious for i in offence_ids)
    nxt = actions.next_steps(offence_ids, categories, merged, procedure, serious, lang)

    extra_laws = []
    if merged.get("online") == "Yes" and {"cheating", "impersonation"} & set(offence_ids):
        extra_laws.append({"law": "Information Technology Act, 2000", "sections": "s. 66C (identity theft), s. 66D (cheating by personation using a computer resource)",
                           "note": "Outside the LegalCompass mapping (special statute) — shown for awareness."})

    similar = cases.similar(rules_text, sorted(used))
    explanation = None
    if ready and llm.enabled():
        # wording only, in parallel; personal details are masked before anything leaves the server
        masked = summary.mask(narrative)
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_exp = pool.submit(llm.explain, masked, law, [s["bns"][0]["provision"] if (law == "BNS" and s["bns"]) else f"IPC {s['ipc']}" for s in sections]) if sections else None
            f_cases = pool.submit(llm.summarise_cases, masked, [c["snippet"] + (f" [Decision sentence: {c['outcome_text']}]" if c.get("outcome_text") else "") for c in similar["results"]], lang) if similar.get("results") else None
            explanation = f_exp.result() if f_exp else None
            sums = f_cases.result() if f_cases else None
        if sums:
            for c, sm in zip(similar["results"], sums):
                c["plain"] = sm
            similar["plain_by"] = llm.status()["model"]

    return {
        "ready": ready,
        "questions": [] if finalize else questions,
        "required_missing": required_missing,
        "facts": ex["facts"],
        "answers": merged,
        "inferred": {k: v for k, v in ex["inferred"].items() if k not in user_answers},
        # definitions for facts read from the text, so the user can correct them on the questions screen
        "inferred_questions": [{"id": QUESTIONS[k].id, "kind": QUESTIONS[k].kind, "options": QUESTIONS[k].options, "required": QUESTIONS[k].required,
                                **i18n.question(k, lang, QUESTIONS[k].text, QUESTIONS[k].why, QUESTIONS[k].options)}
                               for k in ex["inferred"] if k in QUESTIONS],
        "offences": [{"id": m["id"], "label": i18n.offence(m["id"], lang, BY_ID[m["id"]].label), "evidence": m["evidence"]} for m in matched],
        "understood": bool(matched or clf),
        "regime": {**regime, "reason": i18n.regime_reason(regime, lang)},
        "lang": lang,
        "answer_labels": {k: i18n.answer_label(k, v, lang, QUESTIONS[k].options) for k, v in merged.items() if k in QUESTIONS},
        "procedure_code": procedure,
        "primary_code": primary,
        "sections": sections,
        "extra_laws": extra_laws,
        "classifier": {"available": classifier.available(), "top": clf},
        "similar_cases": similar,
        "next_steps": nxt,
        "explanation": explanation,
        "summary": summary.build(narrative, merged, regime, sections, nxt["steps"]),
        "disclaimer": i18n.DISCLAIMER[lang],
    }
