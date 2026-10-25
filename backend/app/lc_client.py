"""Thin client for the existing LegalCompass transition API.

The research repository is not modified or imported: the app talks to it over HTTP, so the mapping served
here is exactly the published dataset (DOI 10.21227/h4wg-7413).
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache

import httpx

from . import config


class LegalCompassUnavailable(RuntimeError):
    pass


def _client() -> httpx.Client:
    headers = {"x-api-key": config.LEGALCOMPASS_API_KEY} if config.LEGALCOMPASS_API_KEY else {}
    return httpx.Client(base_url=config.LEGALCOMPASS_API, headers=headers, timeout=15)


def _get(path: str, **params):
    try:
        with _client() as c:
            r = c.get(path, params={k: v for k, v in params.items() if v is not None})
    except httpx.HTTPError as e:
        raise LegalCompassUnavailable(f"LegalCompass API not reachable at {config.LEGALCOMPASS_API}: {e}") from e
    if r.status_code == 422:
        return None
    if r.status_code in (401, 429):
        raise LegalCompassUnavailable(f"LegalCompass API refused the request ({r.status_code}): {r.text[:200]} "
                                      "- set LEGALCOMPASS_API_KEY to a key listed in the API's SB_API_KEYS.")
    r.raise_for_status()
    return r.json()


@lru_cache(maxsize=4096)
def lookup(code: str, section: str) -> dict | None:
    return _get(f"/v1/map/{code}/{section}")


@lru_cache(maxsize=2048)
def section_text(code: str, section: str) -> dict | None:
    return _get(f"/v1/sections/{code}/{section}")


def convert_text(text: str) -> dict:
    """Rewrite every unambiguous citation in a document; ambiguous ones are listed, not guessed."""
    try:
        with _client() as c:
            r = c.post("/v1/convert/text", json={"text": text})
    except httpx.HTTPError as e:
        raise LegalCompassUnavailable(f"LegalCompass API not reachable at {config.LEGALCOMPASS_API}: {e}") from e
    if r.status_code in (401, 429):
        raise LegalCompassUnavailable(f"LegalCompass API refused the request ({r.status_code}).")
    r.raise_for_status()
    return r.json()


def applicable_law(offence_date: date | None, offence_end_date: date | None = None,
                   proceedings_start_date: date | None = None) -> dict:
    return _get("/v1/applicable-law",
                offence_date=offence_date and offence_date.isoformat(),
                offence_end_date=offence_end_date and offence_end_date.isoformat(),
                proceedings_start_date=proceedings_start_date and proceedings_start_date.isoformat())


def health() -> bool:
    return check()["ok"]


def check() -> dict:
    """Reachability of the mapping API, with the reason when it fails (shown on /api/status)."""
    try:
        with _client() as c:
            r = c.get("/v1/map/IPC/420")
        if r.status_code == 200:
            return {"ok": True, "url": config.LEGALCOMPASS_API}
        return {"ok": False, "url": config.LEGALCOMPASS_API,
                "error": f"HTTP {r.status_code}: {r.text[:150]}" + (" - API keys differ" if r.status_code in (401, 429) else "")}
    except Exception as e:
        return {"ok": False, "url": config.LEGALCOMPASS_API, "error": f"{type(e).__name__}: {e}"[:200]}
