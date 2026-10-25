"""Settings, all from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """Read KEY=value lines from backend/.env (git-ignored) without overriding real environment variables."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file(BASE / ".env")
DATA = Path(os.environ.get("LCAPP_DATA", BASE / "data"))

# The existing LegalCompass transition API (research repo, run unchanged as a separate service)
LEGALCOMPASS_API = os.environ.get("LEGALCOMPASS_API", "http://127.0.0.1:8000").rstrip("/")
LEGALCOMPASS_API_KEY = os.environ.get("LEGALCOMPASS_API_KEY", "")

# Optional local artefacts built from IL-TUR on your own machine (never committed: licence forbids redistribution)
CLASSIFIER_PATH = Path(os.environ.get("IPC_CLASSIFIER", DATA / "ipc_classifier.joblib"))
CASE_INDEX_PATH = Path(os.environ.get("CASE_INDEX", DATA / "case_index.joblib"))

# Optional LLM (any OpenAI-compatible endpoint). Leave empty to run rule-only.
# With just LLM_API_KEY set, the provider is recognised from the key: xAI Grok ("xai-...") or Groq ("gsk_...").
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
_PROVIDERS = {"xai-": ("xAI Grok", "https://api.x.ai/v1", "grok-3-mini"),  # fallback only: the app picks a current model from /models
              "gsk_": ("Groq", "https://api.groq.com/openai/v1", "openai/gpt-oss-20b")}
_p = next((v for k, v in _PROVIDERS.items() if LLM_API_KEY.startswith(k)), None)
LLM_BASE_URL = (os.environ.get("LLM_BASE_URL") or (_p[1] if _p else "")).rstrip("/")
LLM_MODEL_EXPLICIT = bool(os.environ.get("LLM_MODEL"))
LLM_MODEL = os.environ.get("LLM_MODEL") or (_p[2] if _p else "")
LLM_PROVIDER = _p[0] if _p and LLM_BASE_URL == _p[1] else ("custom" if LLM_BASE_URL else None)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
# e.g. https://.*\.vercel\.app to allow the deployed website and its preview links
CORS_ORIGIN_REGEX = os.environ.get("CORS_ORIGIN_REGEX", "")
