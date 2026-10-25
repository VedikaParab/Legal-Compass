"""Tiny Python client. Works against a running server (base_url) or in-process (no server needed).

    from sb_api.client import SanhitaBridge
    sb = SanhitaBridge()                                  # in-process
    sb = SanhitaBridge("https://api.example.org")         # remote
    sb.map("IPC", "420")["results"][0]["new"]["provision"]   # 'BNS 318(4)'
    sb.convert("Booked u/s 302/34 IPC")["converted_text"]
"""
from __future__ import annotations


class SanhitaBridge:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = 30):
        if base_url:
            import httpx
            self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout,
                                      headers={"x-api-key": api_key} if api_key else {})
        else:
            from fastapi.testclient import TestClient
            from .main import app
            self._http = TestClient(app)

    def _get(self, path, **params):
        r = self._http.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()

    def _post(self, path, body):
        r = self._http.post(path, json=body)
        r.raise_for_status()
        return r.json()

    def meta(self):
        return self._get("/v1/meta")

    def map(self, code, section):
        return self._get(f"/v1/map/{code}/{section}")

    def new_for(self, code, section) -> list[str]:
        """Convenience: just the counterpart provision IDs, e.g. ['BNS 318(4)']."""
        res = self.map(code, section)
        side = "new" if res["direction"] == "old_to_new" else "old"
        return sorted({r[side]["provision"] or "NEW" for r in res["results"]})

    def batch(self, citations):
        return self._post("/v1/map/batch", {"citations": list(citations)})

    def compare(self, row_id):
        return self._get(f"/v1/compare/{row_id}")

    def section(self, code, section):
        return self._get(f"/v1/sections/{code}/{section}")

    def search(self, q, code=None, limit=20):
        return self._get("/v1/search", q=q, code=code, limit=limit)

    def convert(self, text, annotate_original=True):
        return self._post("/v1/convert/text", {"text": text, "annotate_original": annotate_original})

    def applicable_law(self, offence_date=None, offence_end_date=None, proceedings_start_date=None):
        return self._get("/v1/applicable-law", offence_date=offence_date, offence_end_date=offence_end_date,
                         proceedings_start_date=proceedings_start_date)

    def export(self, pair=None):
        return self._get("/v1/export", format="json", pair=pair)
