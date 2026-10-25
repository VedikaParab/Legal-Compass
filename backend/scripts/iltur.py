"""Load IL-TUR's statute-identification (LSI) split, on YOUR machine.

IL-TUR is gated on Hugging Face (https://huggingface.co/datasets/Exploration-Lab/IL-TUR). Either
  * log in once:  huggingface-cli login   (or set HF_TOKEN), then run the scripts with no --iltur-dir, or
  * download the repo and pass --iltur-dir /path/to/IL-TUR
The data and anything built from it stay local: the IL-TUR licence does not allow redistribution.

Label handling matches the LegalCompass paper (same 13 excluded labels).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

EXCLUDED_LABELS = {"13", "161", "164", "155", "156", "173", "190", "200", "482", "2", "3", "4", "5"}


def _readme_names(root: Path):
    import yaml
    for f in (root / "README.md", root / "lsi" / "README.md", root.parent / "README.md"):
        if not f.exists():
            continue
        m = re.match(r"^---\s*\n(.*?)\n---", f.read_text(encoding="utf-8", errors="ignore"), re.S)
        if not m:
            continue
        for cfg in (yaml.safe_load(m.group(1)) or {}).get("dataset_info", []) or []:
            if cfg.get("config_name") != "lsi":
                continue
            for feat in cfg.get("features", []):
                if feat.get("name") == "labels":
                    node = feat.get("sequence", feat.get("list", feat))
                    node = node.get("class_label", node) if isinstance(node, dict) else node
                    names = node.get("names") if isinstance(node, dict) else None
                    if names:
                        return [names[k] for k in sorted(names, key=int)] if isinstance(names, dict) else list(names)
    return None


def _local(root):
    root = Path(root)
    lsi = root / "lsi" if (root / "lsi").is_dir() else root
    out = {}
    for split in ("train", "dev", "test"):
        files = sorted(lsi.glob(f"*{split}*.parquet")) or sorted(lsi.glob(f"*{split}*.jsonl"))
        if files:
            out[split] = pd.concat([pd.read_parquet(f) if f.suffix == ".parquet" else pd.read_json(f, lines=True)
                                    for f in files], ignore_index=True)
    if not out:
        raise FileNotFoundError(f"no LSI parquet/jsonl files under {lsi}")
    return out, _readme_names(lsi) or _readme_names(lsi.parent)


def _hub():
    from datasets import load_dataset
    ds = load_dataset("Exploration-Lab/IL-TUR", "lsi")  # uses your HF login / HF_TOKEN
    f = ds["train"].features["labels"]
    names = f.feature.names if hasattr(f, "feature") and hasattr(f.feature, "names") else None
    return {k: ds[k].to_pandas() for k in ds}, names


def _as_list(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


def load_lsi(iltur_dir: str | None = None) -> dict[str, pd.DataFrame]:
    """{split: DataFrame(id, text, ipc)} with IPC section strings and excluded labels removed."""
    splits, names = _local(iltur_dir) if iltur_dir else _hub()
    out = {}
    for split, df in splits.items():
        rows = []
        for ex in df.to_dict("records"):
            labels = _as_list(ex["labels"])
            labels = [names[int(i)] if (names and not isinstance(i, str)) else str(i) for i in labels]
            ipc = sorted({m.group(1) for l in labels if (m := re.search(r"(\d+[A-Z]*)", str(l)))} - EXCLUDED_LABELS)
            if not ipc:
                continue
            text = ex["text"] if isinstance(ex["text"], str) else " ".join(_as_list(ex["text"]))
            rows.append({"id": str(ex.get("id", len(rows))), "text": text, "ipc": ipc})
        out[split] = pd.DataFrame(rows)
    return out


def fake_lsi(api: str, key: str = "") -> dict[str, pd.DataFrame]:
    """Synthetic stand-in built from IPC section texts (for testing the scripts without IL-TUR)."""
    import random
    import httpx
    random.seed(0)
    h = {"x-api-key": key} if key else {}
    secs = ["302", "307", "323", "324", "325", "354", "376", "379", "380", "392", "406", "420", "498A", "506", "34", "447"]
    texts = {}
    for s in secs:
        r = httpx.get(f"{api}/v1/sections/IPC/{s}", headers=h, timeout=10).json()
        texts[s] = r.get("title", "") + ". " + r.get("text", "")
    out = {}
    for split, n in (("train", 300), ("dev", 80), ("test", 80)):
        rows = []
        for i in range(n):
            ipc = sorted(random.sample(secs, random.choice([1, 2])))
            rows.append({"id": f"{split}{i}", "text": " ".join(texts[s] for s in ipc), "ipc": ipc})
        out[split] = pd.DataFrame(rows)
    return out
