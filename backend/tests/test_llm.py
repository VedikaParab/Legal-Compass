"""LLM layer: provider detection from the key, model discovery, retired-model retry, grounded case summaries.

No real provider is called: httpx is replaced by a fake OpenAI-compatible server.
"""
import importlib
import json

import httpx
import pytest

from app import config, llm


def _reload_config(monkeypatch, **env):
    for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    importlib.reload(config)
    llm.STATE.update(model=None, last_error=None)
    llm._summaries.cache_clear()


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    yield
    for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    importlib.reload(config)
    llm.STATE.update(model=None, last_error=None)


def test_provider_from_key(monkeypatch):
    _reload_config(monkeypatch, LLM_API_KEY="xai-123")
    assert config.LLM_PROVIDER == "xAI Grok" and config.LLM_BASE_URL == "https://api.x.ai/v1"
    _reload_config(monkeypatch, LLM_API_KEY="gsk_123")
    assert config.LLM_PROVIDER == "Groq" and config.LLM_BASE_URL.startswith("https://api.groq.com")
    _reload_config(monkeypatch)
    assert not llm.enabled()


class Fake:
    """Minimal OpenAI-compatible server: lists models, rejects retired ones, returns canned JSON."""
    def __init__(self, models, reply, retired=()):
        self.models, self.reply, self.retired, self.calls = models, reply, set(retired), []

    def get(self, url, **kw):
        return httpx.Response(200, json={"data": [{"id": m} for m in self.models]}, request=httpx.Request("GET", url))

    def post(self, url, json=None, **kw):
        self.calls.append(json["model"])
        req = httpx.Request("POST", url)
        if json["model"] in self.retired:
            return httpx.Response(404, text='{"error": "The model does not exist"}', request=req)
        return httpx.Response(200, json={"choices": [{"message": {"content": self.reply}}]}, request=req)


def test_discovers_fast_model_and_summarises(monkeypatch):
    _reload_config(monkeypatch, LLM_API_KEY="xai-123")
    reply = json.dumps({"cases": [{"summary": "Money was taken from a bank account by cheque.", "outcome": "not stated", "relevance": "Both involve Rs 45,000 taken from a bank account."}]})
    fake = Fake(["grok-imagine-image", "grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning", "grok-code-fast-1"], "Here you go: " + reply)
    monkeypatch.setattr(llm.httpx, "get", fake.get)
    monkeypatch.setattr(llm.httpx, "post", fake.post)
    out = llm.summarise_cases("I lost Rs 45,000", ["The accused withdrew Rs.45,000 by cheque."])
    assert fake.calls == ["grok-4-1-fast-non-reasoning"]
    assert out[0]["outcome"] == "not stated" and "bank" in out[0]["summary"]


def test_retired_default_model_is_replaced(monkeypatch):
    _reload_config(monkeypatch, LLM_API_KEY="gsk_123")
    fake = Fake(["openai/gpt-oss-20b"], "ok", retired={"openai/gpt-oss-20b-old"})
    monkeypatch.setattr(llm.httpx, "get", lambda *a, **k: httpx.Response(500, request=httpx.Request("GET", "x")))
    monkeypatch.setattr(llm.httpx, "post", fake.post)
    config.LLM_MODEL = "openai/gpt-oss-20b-old"  # as if the built-in default had been retired
    llm.STATE["model"] = None
    monkeypatch.setattr(llm.httpx, "get", fake.get)
    llm.STATE["model"] = "openai/gpt-oss-20b-old"
    assert llm.chat("s", "u") == "ok"
    assert fake.calls == ["openai/gpt-oss-20b-old", "openai/gpt-oss-20b"]


def test_bad_reply_gives_no_summaries(monkeypatch):
    _reload_config(monkeypatch, LLM_API_KEY="gsk_123", LLM_MODEL="m")
    fake = Fake([], '{"cases": [{"summary": "only one"}]}')
    monkeypatch.setattr(llm.httpx, "post", fake.post)
    assert llm.summarise_cases("x", ["p1", "p2"]) is None  # wrong count -> show the passages without summaries
    assert "JSON" in llm.status()["last_error"]
