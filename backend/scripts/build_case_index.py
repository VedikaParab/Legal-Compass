"""Build the similar-case index from IL-TUR judgments (run locally; output stays on your machine).

    python scripts/build_case_index.py                       # uses your Hugging Face login
    python scripts/build_case_index.py --iltur-dir ~/IL-TUR
    python scripts/build_case_index.py --fake                # smoke test

Indexes the facts of IL-TUR statute-identification judgments (train + dev + test) with TF-IDF and keeps each
judgment's IPC labels, so the app can filter similar cases by case type. Writes data/case_index.joblib.
"""
import argparse
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).parent))
from iltur import fake_lsi, load_lsi  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iltur-dir")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--max-docs", type=int, default=60000)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "case_index.joblib"))
    a = ap.parse_args()
    data = fake_lsi(os.environ.get("LEGALCOMPASS_API", "http://localhost:8000"), os.environ.get("LEGALCOMPASS_API_KEY", "")) \
        if a.fake else load_lsi(a.iltur_dir)
    df = pd.concat([d.assign(split=k) for k, d in data.items()], ignore_index=True).head(a.max_docs)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1 if a.fake else 3, max_features=200_000, sublinear_tf=True,
                          stop_words="english")
    M = vec.fit_transform(df.text.map(lambda t: " ".join(t.split()[:600])))
    # keep the first ~350 words so the app can show the passage that best matches the user's description
    meta = [{"id": f"{r.split}:{r.id}", "ipc": list(r.ipc), "snippet": " ".join(r.text.split()[:70]) + " ...",
             "text": " ".join(r.text.split()[:350])} for r in df.itertuples()]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vec": vec, "matrix": M, "meta": meta,
                 "source": "synthetic test data" if a.fake else "IL-TUR LSI (research use only, not for redistribution)"}, a.out, compress=3)
    print(f"indexed {len(meta)} judgments -> {a.out}")


if __name__ == "__main__":
    main()
