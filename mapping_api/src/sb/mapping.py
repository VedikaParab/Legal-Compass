"""Single loader for the SanhitaBridge mapping table.

Canonical source (public release, DOI 10.21227/h4wg-7413):
    data/raw/Criminal_Law_Transition_Mapping_cleaned_final.xlsx  (sheet All_Mappings, 21 columns)
Fallback (internal cleaning output with review columns):
    data/raw/mapping_clean_v1.csv

Override with the env var SB_MAPPING=<path to .xlsx or .csv>, or with the URL of a running SanhitaBridge API
(e.g. SB_MAPPING=https://api.example.org) so the research pipeline reads exactly what the public API serves.
The public release drops the internal review/provenance columns; they are filled with neutral defaults
so every downstream script (benchmark, API, app) sees the same schema.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
FINAL = RAW / "Criminal_Law_Transition_Mapping_cleaned_final.xlsx"
LEGACY = RAW / "mapping_clean_v1.csv"

CORE_COLUMNS = [
    "row_id", "code_pair", "old_code", "old_section", "old_subsection", "old_provision_id", "old_section_raw",
    "old_heading", "new_code", "new_section", "new_subsection", "new_provision_id", "new_heading",
    "mapping_type", "mapping_type_section", "substantive_change", "notes",
    "mapping_type_annotated", "mapping_type_section_annotated", "source_doc", "source_page",
]
OPTIONAL_DEFAULTS = {"needs_review": "False", "review_reasons": "", "cleaning_actions": ""}
MAPPING_TYPES = {"one_to_one", "merged", "split", "many_to_many", "new", "new_in_existing_section"}
CHANGE_VALUES = {"Y", "N", "unclear"}


def source_path() -> Path:
    env = os.environ.get("SB_MAPPING")
    if env:
        return Path(env)
    return FINAL if FINAL.exists() else LEGACY


def load_mapping(path: str | Path | None = None, validate: bool = True) -> pd.DataFrame:
    """Return the mapping as a DataFrame of strings ("" for missing), canonical column order first."""
    raw = str(path) if path else os.environ.get("SB_MAPPING", "")
    if raw.startswith(("http://", "https://")):
        import json
        import urllib.request
        with urllib.request.urlopen(raw.rstrip("/") + "/v1/export?format=json", timeout=60) as r:
            df = pd.DataFrame(json.load(r)["rows"]).fillna("").astype(str)
        if validate:
            validate_mapping(df, raw)
        df.attrs["source"] = raw
        return df
    p = Path(path) if path else source_path()
    if p.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(p, sheet_name="All_Mappings", dtype=str)
    else:
        df = pd.read_csv(p, dtype=str)
    df = df.fillna("")
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    missing = [c for c in CORE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{p.name}: missing required columns {missing}")
    for c, v in OPTIONAL_DEFAULTS.items():
        if c not in df.columns:
            df[c] = v
    extra = [c for c in df.columns if c not in CORE_COLUMNS]
    df = df[CORE_COLUMNS + extra]
    if validate:
        validate_mapping(df, p.name)
    df.attrs["source"] = str(p)
    return df


def validate_mapping(df: pd.DataFrame, name: str = "mapping") -> None:
    errs = []
    if df.row_id.duplicated().any():
        errs.append(f"duplicate row_id: {df.row_id[df.row_id.duplicated()].tolist()[:5]}")
    bad_mt = set(df.mapping_type_section) - MAPPING_TYPES
    if bad_mt:
        errs.append(f"unknown mapping_type_section {bad_mt}")
    bad_sc = set(df.substantive_change) - CHANGE_VALUES
    if bad_sc:
        errs.append(f"unknown substantive_change {bad_sc}")
    if (df.new_section == "").any():
        errs.append(f"{int((df.new_section == '').sum())} rows without new_section")
    pairs = set(df.code_pair)
    if not pairs <= {"IPC_to_BNS", "CrPC_to_BNSS", "IEA_to_BSA"}:
        errs.append(f"unexpected code_pair {pairs}")
    if errs:
        raise ValueError(f"{name}: " + "; ".join(errs))


if __name__ == "__main__":
    d = load_mapping()
    print(d.attrs["source"], len(d), "rows")
    print(d.code_pair.value_counts().to_dict())
    print(d.mapping_type_section.value_counts().to_dict())
    print(d.substantive_change.value_counts().to_dict())
