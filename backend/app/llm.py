"""Optional LLM helper (OpenAI-compatible: xAI Grok, Groq, Ollama, vLLM...). Used only for wording.

Sections are never taken from the LLM: they come from the offence rules / classifier and are always passed
through the LegalCompass mapping, so the app cannot cite a section that does not exist. Personal details in the
description are masked before anything is sent.
"""
from __future__ import annotations

import json
import re
import threading
from functools import lru_cache

import httpx

from . import config

STATE = {"model": None, "last_error": None}
_lock = threading.Lock()

# preference when LLM_MODEL is not set: fast, non-reasoning chat models first (newest name wins within a rule)
PREFER = [r"fast.*non-reasoning", r"gpt-oss-20b", r"mini", r"fast", r"gpt-oss-120b", r"llama-3\.3-70b", r"llama", r"grok", r"."]
SKIP = re.compile(r"image|vision|imagine|video|audio|whisper|tts|embed|guard|moderation|code|search", re.I)


def enabled() -> bool:
    return bool(config.LLM_BASE_URL and (config.LLM_MODEL or config.LLM_API_KEY))


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.LLM_API_KEY or 'EMPTY'}"}


def _discover() -> str | None:
    """Pick a chat model from the provider's /models list (names change often)."""
    try:
        r = httpx.get(f"{config.LLM_BASE_URL}/models", headers=_headers(), timeout=15)
        r.raise_for_status()
        ids = sorted({m["id"] for m in r.json().get("data", []) if not SKIP.search(m["id"])}, reverse=True)
    except Exception as e:
        STATE["last_error"] = f"model list: {type(e).__name__}: {e}"[:200]
        return None
    for rule in PREFER:
        for i in ids:
            if re.search(rule, i):
                return i
    return None


def model() -> str | None:
    with _lock:
        if STATE["model"] is None:
            STATE["model"] = config.LLM_MODEL if config.LLM_MODEL_EXPLICIT else (_discover() or config.LLM_MODEL or None)
        return STATE["model"]


def status() -> dict:
    return {"enabled": enabled(), "provider": config.LLM_PROVIDER, "model": STATE["model"] or config.LLM_MODEL or "auto",
            **({"last_error": STATE["last_error"]} if STATE["last_error"] else {})}


def chat(system: str, user: str, max_tokens: int = 400, retry: bool = True) -> str | None:
    if not enabled() or not model():
        return None
    try:
        r = httpx.post(f"{config.LLM_BASE_URL}/chat/completions", timeout=60, headers=_headers(),
                       json={"model": STATE["model"], "temperature": 0, "max_tokens": max_tokens,
                             "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        if r.status_code in (400, 404) and retry and "model" in r.text.lower() and not config.LLM_MODEL_EXPLICIT:
            STATE["model"] = None  # the default model was retired: pick another from the list and try once more
            config.LLM_MODEL = ""
            return chat(system, user, max_tokens, retry=False)
        r.raise_for_status()
        STATE["last_error"] = None
        return (r.json()["choices"][0]["message"].get("content") or "").strip() or None
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        if isinstance(e, httpx.HTTPStatusError):
            msg = f"HTTP {e.response.status_code}: {e.response.text[:150]}"
        STATE["last_error"] = msg[:200]
        return None


def explain(narrative: str, law: str | None, sections: list[str]) -> str | None:
    sys = ("You explain Indian criminal law to a non-lawyer in simple English. Use ONLY the sections given. "
           "Do not add new sections, do not predict outcomes, and end by advising them to confirm with a lawyer. "
           "Maximum 120 words.")
    user = f"Situation: {narrative[:2000]}\nApplicable code: {law or 'not decided'}\nSections: {', '.join(sections)}"
    return chat(sys, user)


def translate_to_english(text: str) -> str | None:
    return chat("Translate the user's text from Hindi or Marathi to plain English. Output only the translation.",
                text[:3000], max_tokens=600)


LANG_NAME = {"en": "simple English", "hi": "simple Hindi (Devanagari)", "mr": "simple Marathi (Devanagari)"}
CASE_SYS = """You rewrite short passages from Indian court judgments for a non-lawyer.
Rules:
- Use ONLY what the passage says. Never add facts, courts, dates, sections or results that are not written in it.
- Names were removed from the passages; refer to people by role (complainant, accused, petitioner) or as "a person".
- "summary": one or two short sentences on what the passage says happened.
- "outcome": what the court decided ONLY if the passage (or its "Decision sentence") states it; otherwise exactly "not stated".
- "relevance": one short sentence on what it has in common with the user's situation, or "unclear".
Reply with JSON only: {"cases": [{"summary": "...", "outcome": "...", "relevance": "..."}, ...]} in the same order."""


@lru_cache(maxsize=512)
def _summaries(situation: str, passages: tuple[str, ...], lang: str) -> tuple[dict, ...] | None:
    user = (f"Write the values in {LANG_NAME.get(lang, 'simple English')} (keep the JSON keys and the words "
            f'"not stated" / "unclear" in English).\nUser\'s situation: {situation[:1200]}\n\n'
            + "\n\n".join(f"Passage {i + 1}: {p}" for i, p in enumerate(passages)))
    out = chat(CASE_SYS, user, max_tokens=1600)
    if not out:
        return None
    m = re.search(r"\{.*\}", out, re.S)
    try:
        items = json.loads(m.group(0))["cases"] if m else None
    except (ValueError, KeyError, TypeError):
        items = None
    if not isinstance(items, list) or len(items) != len(passages):
        STATE["last_error"] = "case summaries: reply was not the expected JSON"
        return None
    clean = []
    for it in items:
        it = it if isinstance(it, dict) else {}
        clean.append({k: str(it.get(k, "")).strip()[:400] for k in ("summary", "outcome", "relevance")})
    return tuple(clean)


def summarise_cases(situation: str, passages: list[str], lang: str = "en") -> list[dict] | None:
    """Plain-language, passage-grounded summaries for the similar cases (one batched call, cached)."""
    if not enabled() or not passages:
        return None
    r = _summaries(situation, tuple(passages), lang)
    return list(r) if r else None
