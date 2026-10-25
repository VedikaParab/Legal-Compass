"""Train the IPC statute classifier on IL-TUR (run locally; output stays on your machine).

    python scripts/train_classifier.py                      # uses your Hugging Face login
    python scripts/train_classifier.py --iltur-dir ~/IL-TUR # or a downloaded copy
    python scripts/train_classifier.py --fake               # smoke test without IL-TUR

Same model as the LegalCompass paper: TF-IDF (1-2 grams) + one-vs-rest logistic regression, with one threshold
tuned for micro-F1 on the dev split. Writes data/ipc_classifier.joblib, which the app picks up automatically.
"""
import argparse
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

sys.path.insert(0, str(Path(__file__).parent))
from iltur import fake_lsi, load_lsi  # noqa: E402

MAX_WORDS = 900


def cut(t):
    return " ".join(t.split()[:MAX_WORDS])


def micro_f1(pred, gold):
    tp = sum(len(set(p) & set(g)) for p, g in zip(pred, gold))
    np_, ng = sum(map(len, pred)), sum(map(len, gold))
    p, r = tp / max(np_, 1), tp / max(ng, 1)
    return 2 * p * r / (p + r) if p + r else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iltur-dir")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "ipc_classifier.joblib"))
    a = ap.parse_args()
    data = fake_lsi(os.environ.get("LEGALCOMPASS_API", "http://localhost:8000"), os.environ.get("LEGALCOMPASS_API_KEY", "")) \
        if a.fake else load_lsi(a.iltur_dir)
    tr, dv = data["train"], data.get("dev", data.get("test"))
    min_df = 1 if a.fake else 3
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=min_df, max_features=300_000, sublinear_tf=True)
    X = vec.fit_transform(tr.text.map(cut))
    mlb = MultiLabelBinarizer()
    Y = mlb.fit_transform(tr.ipc)
    print(f"training on {X.shape[0]} judgments, {X.shape[1]} features, {Y.shape[1]} IPC labels ...")
    clf = OneVsRestClassifier(LogisticRegression(C=8, max_iter=2000, solver="liblinear"), n_jobs=-1).fit(X, Y)
    P = clf.predict_proba(vec.transform(dv.text.map(cut)))
    best = (0.0, 0.5)
    for th in np.linspace(0.05, 0.6, 23):
        pred = [[mlb.classes_[j] for j in np.where(p >= th)[0]] or [mlb.classes_[int(p.argmax())]] for p in P]
        best = max(best, (micro_f1(pred, list(dv.ipc)), float(th)))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vec": vec, "clf": clf, "mlb": mlb, "threshold": best[1], "dev_micro_f1": best[0],
                 "source": "fake" if a.fake else "IL-TUR LSI"}, a.out)
    print(f"saved {a.out}  (dev micro-F1 {best[0]:.3f} at threshold {best[1]:.2f})")


if __name__ == "__main__":
    main()
