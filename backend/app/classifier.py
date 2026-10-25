"""Optional IPC statute classifier trained on IL-TUR (see scripts/train_classifier.py).

If the model file is absent the app runs on the rule-based offence catalogue alone.
"""
from __future__ import annotations

from functools import lru_cache

from . import config

MAX_WORDS = 900


@lru_cache(maxsize=1)
def load():
    if not config.CLASSIFIER_PATH.exists():
        return None
    import warnings

    import joblib
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # minor scikit-learn version differences between training and serving
        return joblib.load(config.CLASSIFIER_PATH)


def available() -> bool:
    return config.CLASSIFIER_PATH.exists()


def predict(text: str, k: int = 5) -> list[dict]:
    obj = load()
    if obj is None:
        return []
    words = text.split()
    p = obj["clf"].predict_proba(obj["vec"].transform([" ".join(words[:MAX_WORDS])]))[0]
    order = p.argsort()[::-1][:k]
    th = obj.get("threshold", 0.3)
    return [{"ipc": str(obj["mlb"].classes_[i]), "prob": float(p[i]), "above_threshold": bool(p[i] >= th)}
            for i in order]
