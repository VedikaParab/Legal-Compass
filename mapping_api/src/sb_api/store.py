"""In-memory store for the SanhitaBridge API: mapping rows + statute text + full-text search.

Everything is built at start-up from the same two files the research pipeline uses
(src/sb/mapping.py and data/raw/statutes_sections.json), so the API and the paper never disagree.
`export_bundle()` writes the same data as SQLite (FTS5) + JSON for offline/mobile clients.
"""
from __future__ import annotations

import difflib
import json
import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sb.corpus import PAIRS, get, load_corpus, provision_text
from sb.mapping import load_mapping

DATASET_META = {
    "name": "SanhitaBridge: Indian Criminal Law Transition Mapping (IPC-BNS, CrPC-BNSS, IEA-BSA)",
    "doi": "10.21227/h4wg-7413",
    "licence": "CC BY 4.0",
    "commencement": "2024-07-01",
    "citation": "P. Patil, V. Parab, J. Kathpal, \"Indian Criminal Law Transition Mapping Dataset: IPC-BNS, "
                "CrPC-BNSS, and IEA-BSA,\" IEEE DataPort, doi:10.21227/h4wg-7413",
    "disclaimer": "Research and reference aid only; not legal advice. Always verify against the official Gazette text "
                  "of the Act before relying on a mapping in court or in a filing.",
}

OLD_TO_NEW = {"IPC": "BNS", "CrPC": "BNSS", "IEA": "BSA"}
NEW_TO_OLD = {v: k for k, v in OLD_TO_NEW.items()}
CODE_PAIR = {oc: p for p, (oc, _) in PAIRS.items()} | {nc: p for p, (_, nc) in PAIRS.items()}
CODE_NAMES = {
    "IPC": "Indian Penal Code, 1860", "CrPC": "Code of Criminal Procedure, 1973", "IEA": "Indian Evidence Act, 1872",
    "BNS": "Bharatiya Nyaya Sanhita, 2023", "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "BSA": "Bharatiya Sakshya Adhiniyam, 2023",
}
MAPPING_TYPE_PLAIN = {
    "one_to_one": "Moved as a whole to one new provision.",
    "merged": "Several old provisions were combined into this new section.",
    "split": "The old section was divided across several new provisions - check which part applies.",
    "many_to_many": "Parts of several old sections and several new sections overlap - read both texts.",
    "new": "New provision with no counterpart in the old code.",
    "new_in_existing_section": "New sub-provision added inside an existing section.",
}
CHANGE_PLAIN = {"Y": "The text changed (see note).", "N": "No change in substance.",
                "unclear": "Change status could not be determined - read both texts."}


def canon_code(code: str) -> str:
    c = re.sub(r"[^a-z]", "", code.lower())
    table = {"ipc": "IPC", "crpc": "CrPC", "iea": "IEA", "bns": "BNS", "bnss": "BNSS", "bsa": "BSA"}
    if c not in table:
        raise KeyError(f"unknown code '{code}' (use IPC, CrPC, IEA, BNS, BNSS or BSA)")
    return table[c]


def split_section(raw: str) -> tuple[str, str]:
    """'376(2)(n)' -> ('376', '(2)(n)');  '498-A' -> ('498A', '')."""
    s = re.sub(r"\s+", "", str(raw)).replace("-", "").upper()
    m = re.fullmatch(r"(\d{1,3}[A-Z]{0,2})((?:\(\w{1,4}\))*)", s)
    if not m:
        raise ValueError(f"cannot parse section '{raw}'")
    return m.group(1), m.group(2).lower()


@dataclass
class Store:
    rows: list[dict]
    by_old: dict
    by_new: dict
    by_id: dict
    db: sqlite3.Connection
    source: str

    # ------------------------------------------------------------------ lookups
    def section(self, code: str, number: str) -> dict | None:
        s = get(code, number)
        if s is None:
            return None
        return {"code": code, "section": s.number, "title": s.title, "chapter": s.chapter,
                "text": s.text, "act": CODE_NAMES[code]}

    def lookup(self, code: str, section: str) -> dict:
        """Old code -> new provisions, or new code -> old provisions. Sub-section narrows the result when it matches."""
        code = canon_code(code)
        base, sub = split_section(section)
        old_side = code in OLD_TO_NEW
        idx = self.by_old if old_side else self.by_new
        rows = idx.get((code, base), [])
        if sub:
            key = "old_subsection" if old_side else "new_subsection"
            narrowed = [r for r in rows if r[key] and (r[key] == sub or r[key].startswith(sub) or sub.startswith(r[key]))]
            rows = narrowed or rows
        target = OLD_TO_NEW.get(code) or NEW_TO_OLD[code]
        exists = get(code, base) is not None
        if rows:
            status = "mapped" if len({self._target_id(r, old_side) for r in rows}) == 1 else "multiple_targets"
        else:
            status = "not_in_mapping" if exists else "unknown_section"
        return {
            "query": {"code": code, "section": base, "subsection": sub or None, "act": CODE_NAMES[code]},
            "direction": "old_to_new" if old_side else "new_to_old",
            "target_code": target,
            "status": status,
            "message": self._message(status, code, base, target),
            "results": [self._row_view(r, old_side) for r in rows],
        }

    def _target_id(self, r, old_side):
        return r["new_provision_id"] if old_side else (r["old_provision_id"] or "NEW")

    def _message(self, status, code, base, target):
        return {
            "mapped": f"{code} {base} corresponds to one {target} provision.",
            "multiple_targets": f"{code} {base} corresponds to several {target} provisions - pick the one that fits the facts.",
            "not_in_mapping": f"{code} {base} exists but has no row in the current dataset release (it may be omitted "
                              f"or not yet mapped). Check the official comparison table.",
            "unknown_section": f"{code} {base} was not found in the statute text.",
        }[status]

    def _row_view(self, r, old_side=True):
        return {
            "row_id": r["row_id"],
            "old": {"code": r["old_code"], "provision": r["old_provision_id"] or None, "section": r["old_section"] or None,
                    "subsection": r["old_subsection"] or None, "heading": r["old_heading"] or None},
            "new": {"code": r["new_code"], "provision": r["new_provision_id"], "section": r["new_section"],
                    "subsection": r["new_subsection"] or None, "heading": r["new_heading"] or None},
            "mapping_type": r["mapping_type"], "mapping_type_section": r["mapping_type_section"],
            "mapping_type_explained": MAPPING_TYPE_PLAIN.get(r["mapping_type_section"], ""),
            "substantive_change": r["substantive_change"],
            "substantive_change_explained": CHANGE_PLAIN.get(r["substantive_change"], ""),
            "notes": r["notes"] or None,
            "source": {"document": r["source_doc"] or None, "page": r["source_page"] or None},
        }

    def row(self, row_id: str) -> dict | None:
        r = self.by_id.get(row_id)
        return self._row_view(r) if r else None

    # ------------------------------------------------------------------ compare
    def compare(self, row_id: str) -> dict | None:
        r = self.by_id.get(row_id)
        if r is None:
            return None
        ot = provision_text(r["old_code"], r["old_section"], r["old_subsection"], r["old_heading"])[0] if r["old_section"] else None
        nt = provision_text(r["new_code"], r["new_section"], r["new_subsection"], r["new_heading"])[0]
        return {"mapping": self._row_view(r), "old_text": ot, "new_text": nt, "diff": word_diff(ot or "", nt or "")}

    # ------------------------------------------------------------------ search
    def search(self, q: str, code: str | None = None, limit: int = 20) -> list[dict]:
        terms = re.findall(r"\w+", q.lower())
        if not terms:
            return []
        fts = " ".join(f'"{t}"*' for t in terms)
        sql = ("SELECT code, section, title, snippet(sections, 3, '[', ']', ' ... ', 12), bm25(sections, 0, 0, 5.0, 1.0)"
               " AS s FROM sections WHERE sections MATCH ?")
        args = [fts]
        if code:
            sql += " AND code = ?"
            args.append(canon_code(code))
        sql += " ORDER BY s LIMIT ?"
        args.append(limit)
        out = []
        for c, sec, title, snip, score in self.db.execute(sql, args):
            m = self.lookup(c, sec)
            out.append({"code": c, "section": sec, "title": title, "snippet": snip, "score": round(-score, 3),
                        "counterparts": sorted({(x["new"] if c in OLD_TO_NEW else x["old"])["provision"] or "NEW"
                                                for x in m["results"]})})
        return out

    # ------------------------------------------------------------------ export
    def export_rows(self, pair: str | None = None) -> list[dict]:
        return [r for r in self.rows if pair is None or r["code_pair"] == pair]

    def stats(self) -> dict:
        from collections import Counter
        return {
            "rows": len(self.rows),
            "by_pair": dict(Counter(r["code_pair"] for r in self.rows)),
            "mapping_type_section": dict(Counter(r["mapping_type_section"] for r in self.rows)),
            "substantive_change": dict(Counter(r["substantive_change"] for r in self.rows)),
            "sections_with_text": {c: len(v) for c, v in load_corpus().items()},
            "source_file": Path(self.source).name,
        }


def word_diff(a: str, b: str) -> list[dict]:
    """Word-level diff as [{op: equal|insert|delete|replace, old, new}] for side-by-side rendering."""
    aw, bw = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, aw, bw, autojunk=False).get_opcodes():
        out.append({"op": op, "old": " ".join(aw[i1:i2]), "new": " ".join(bw[j1:j2])})
    return out


def _build_db(conn: sqlite3.Connection, rows: list[dict]):
    conn.execute("CREATE VIRTUAL TABLE sections USING fts5(code UNINDEXED, section UNINDEXED, title, text, "
                 "tokenize='porter unicode61')")
    corp = load_corpus()
    alias = {"CRPC": "CrPC"}
    conn.executemany("INSERT INTO sections VALUES (?,?,?,?)",
                     [(alias.get(c, c), s.number, s.title, s.text) for c, secs in corp.items() for s in secs.values()])
    cols = list(rows[0].keys())
    conn.execute(f"CREATE TABLE mapping ({', '.join(c + ' TEXT' for c in cols)})")
    conn.executemany(f"INSERT INTO mapping VALUES ({','.join('?' * len(cols))})", [tuple(r[c] for c in cols) for r in rows])
    conn.execute("CREATE INDEX ix_old ON mapping(old_code, old_section)")
    conn.execute("CREATE INDEX ix_new ON mapping(new_code, new_section)")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.executemany("INSERT INTO meta VALUES (?,?)", list(DATASET_META.items()))
    conn.commit()


@lru_cache(maxsize=1)
def get_store() -> Store:
    df = load_mapping()
    rows = df.to_dict("records")
    by_old, by_new, by_id = {}, {}, {}
    for r in rows:
        if r["old_section"]:
            by_old.setdefault((r["old_code"], r["old_section"].upper()), []).append(r)
        by_new.setdefault((r["new_code"], r["new_section"].upper()), []).append(r)
        by_id[r["row_id"]] = r
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _build_db(conn, rows)
    return Store(rows, by_old, by_new, by_id, conn, df.attrs["source"])


def export_bundle(out_dir: str | Path) -> dict:
    """Write sanhitabridge.sqlite + mapping.json + sections.json for offline clients (PWA, mobile, Excel add-in)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    st = get_store()
    db_path = out / "sanhitabridge.sqlite"
    db_path.unlink(missing_ok=True)
    disk = sqlite3.connect(db_path)
    st.db.backup(disk)
    disk.close()
    (out / "mapping.json").write_text(json.dumps({"meta": DATASET_META, "rows": st.rows}, ensure_ascii=False), encoding="utf-8")
    alias = {"CRPC": "CrPC"}
    secs = {alias.get(c, c): {n: {"title": s.title, "text": s.text} for n, s in v.items()} for c, v in load_corpus().items()}
    (out / "sections.json").write_text(json.dumps(secs, ensure_ascii=False), encoding="utf-8")
    return {p.name: p.stat().st_size for p in out.iterdir()}
