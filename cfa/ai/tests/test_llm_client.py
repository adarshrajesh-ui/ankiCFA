# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Smoke + unit tests for the CFA AI foundation (Feature F0a).

Covers the AI-off contract without any network access, plus one real tiny call
that runs only when a key is actually configured (skipped otherwise). Together
these exercise BOTH branches required by the objective:

  * no key  -> graceful {ok: False}
  * with key -> a real call returning {ok: True}
"""

from __future__ import annotations

import os

import pytest

from cfa.ai import llm_client


@pytest.fixture(autouse=True)
def _clean_usage():
    """Each test starts with fresh per-process usage counters."""
    llm_client.reset_usage()
    yield
    llm_client.reset_usage()


@pytest.fixture
def no_dotenv(monkeypatch):
    """Prevent a developer's real .env from turning off-path tests into calls."""
    monkeypatch.setattr(llm_client, "_load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


# --- AI-off contract --------------------------------------------------------


def test_no_key_returns_graceful_ok_false(no_dotenv):
    r = llm_client.complete("system", "user", purpose="unit_no_key")
    assert r["ok"] is False
    assert r["error"] == "no_api_key"
    assert r["text"] == ""
    assert r["purpose"] == "unit_no_key"
    assert r["usage"]["total_tokens"] == 0


def test_result_shape_is_stable(no_dotenv):
    r = llm_client.complete("s", "u")
    assert set(r.keys()) == {"ok", "text", "model", "usage", "error", "purpose"}
    assert set(r["usage"].keys()) == {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    }


def test_model_override(monkeypatch, no_dotenv):
    monkeypatch.setenv("CFA_LLM_MODEL", "gpt-4o")
    r = llm_client.complete("s", "u")
    assert r["model"] == "gpt-4o"


# --- cost cap (no network needed) -------------------------------------------


def test_cost_cap_blocks_before_calling(monkeypatch):
    # Pretend a key exists but force the token cap to zero: the cap must trip
    # before any client is constructed, so no network call is possible.
    monkeypatch.setattr(llm_client, "_get_api_key", lambda: "sk-fake-not-used")
    monkeypatch.setenv("CFA_LLM_MAX_TOKENS_PER_PROCESS", "0")
    r = llm_client.complete("s", "u", purpose="cap")
    assert r["ok"] is False
    assert r["error"] == "cost_cap_exceeded"


# --- mocked transport (success + retries + key safety) ----------------------


class _FakeUsage:
    prompt_tokens = 11
    completion_tokens = 7
    total_tokens = 18


class _FakeMessage:
    content = "  drafted answer  "


class _FakeChoice:
    message = _FakeMessage()


class _FakeResponse:
    choices = [_FakeChoice()]
    usage = _FakeUsage()


def _install_fake_openai(monkeypatch, behavior):
    """Install a fake `openai.OpenAI` whose create() runs `behavior(attempt)`."""
    calls = {"n": 0}

    class _FakeCompletions:
        def create(self, **kwargs):
            n = calls["n"]
            calls["n"] += 1
            return behavior(n, kwargs)

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self, **kwargs):
            self.chat = _FakeChat()

    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeClient)
    monkeypatch.setattr(llm_client, "_get_api_key", lambda: "sk-SECRET-TOKEN-xyz")
    return calls


def test_success_path_tracks_usage_and_strips_text(monkeypatch):
    _install_fake_openai(monkeypatch, lambda n, kw: _FakeResponse())
    r = llm_client.complete("s", "u", purpose="ok")
    assert r["ok"] is True
    assert r["text"] == "drafted answer"
    assert r["usage"]["total_tokens"] == 18
    assert llm_client.usage_so_far()["tokens"] == 18
    assert llm_client.usage_so_far()["cost_usd"] > 0


def test_retries_transient_then_succeeds(monkeypatch):
    from openai import APIConnectionError

    def behavior(n, kw):
        if n == 0:
            raise APIConnectionError(request=None)  # type: ignore[arg-type]
        return _FakeResponse()

    calls = _install_fake_openai(monkeypatch, behavior)
    monkeypatch.setattr(llm_client.time, "sleep", lambda _s: None)
    r = llm_client.complete("s", "u")
    assert r["ok"] is True
    assert calls["n"] == 2  # one failure + one success


def test_non_retryable_error_classified(monkeypatch):
    from openai import AuthenticationError

    def behavior(n, kw):
        raise AuthenticationError(message="bad key", response=_DummyResp(), body=None)

    _install_fake_openai(monkeypatch, behavior)
    r = llm_client.complete("s", "u")
    assert r["ok"] is False
    assert r["error"] == "auth_error"


def test_key_never_leaks_into_result(monkeypatch):
    from openai import AuthenticationError

    def behavior(n, kw):
        raise AuthenticationError(
            message="sk-SECRET-TOKEN-xyz leaked", response=_DummyResp(), body=None
        )

    _install_fake_openai(monkeypatch, behavior)
    r = llm_client.complete("s", "u")
    assert "SECRET" not in str(r)


class _DummyResp:
    status_code = 401
    headers: dict = {}
    request = None


# --- real call (only when a key is configured) ------------------------------


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="no OPENAI_API_KEY: AI-off"
)
def test_with_key_real_tiny_call():
    r = llm_client.complete(
        system="You reply with exactly one word.",
        user="Reply with the single word: ok",
        max_tokens=5,
        temperature=0.0,
        purpose="smoke_real",
    )
    assert r["ok"] is True, f"real call failed: {r['error']}"
    assert r["text"].strip() != ""
    assert r["usage"]["total_tokens"] > 0
