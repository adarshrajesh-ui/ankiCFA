# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Reusable OpenAI client for the CFA exam-prep AI features.

This is the single entry point every AI feature (ethics grading, tab-to-fill,
etc.) calls. It is designed around a hard rule from the project objective:

    *Every AI feature MUST work fully with AI OFF via a deterministic
    fallback.*

To make that safe, ``complete()`` NEVER raises for an operational problem
(missing key, network error, rate limit, cost cap). Instead it always returns
a structured result dict whose ``ok`` field tells the caller whether to use the
AI ``text`` or fall back to its deterministic path::

    result = complete(system="...", user="...", purpose="grade_ethics")
    if result["ok"]:
        use(result["text"])
    else:
        deterministic_fallback()

Configuration (all optional, read from the process environment / gitignored
``.env`` — see ``.env.example``):

    OPENAI_API_KEY                  the key; absent -> AI OFF (ok=False)
    CFA_LLM_MODEL                   model override (default gpt-4o-mini)
    CFA_LLM_MAX_TOKENS_PER_PROCESS  cumulative token cap (default 200000)
    CFA_LLM_MAX_COST_USD            cumulative USD cap (default 1.00)
    CFA_LLM_MAX_RETRIES             transient-error retries (default 2)

The key is never logged, printed, or included in any returned value or error
string.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Optional, TypedDict

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS_PER_PROCESS = 200_000
DEFAULT_MAX_COST_USD = 1.00
DEFAULT_MAX_RETRIES = 2
_RETRY_BASE_DELAY_S = 0.5

# USD per 1M tokens (input, output). Used only to enforce the local cost cap;
# these are conservative published list prices, not billed amounts. Unknown
# models fall back to the gpt-4o-mini rate so the cap still bounds spend.
_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}


class Usage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CompletionResult(TypedDict):
    ok: bool
    text: str
    model: str
    usage: Usage
    error: Optional[str]
    purpose: str


# --- per-process usage accounting -------------------------------------------

_lock = threading.Lock()
_tokens_used = 0
_cost_used_usd = 0.0


def usage_so_far() -> dict[str, float]:
    """Return the cumulative tokens/cost this process has spent."""
    with _lock:
        return {"tokens": _tokens_used, "cost_usd": round(_cost_used_usd, 6)}


def reset_usage() -> None:
    """Reset the per-process usage counters (used by tests)."""
    global _tokens_used, _cost_used_usd
    with _lock:
        _tokens_used = 0
        _cost_used_usd = 0.0


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    in_rate, out_rate = _PRICING_PER_MTOK.get(model, _PRICING_PER_MTOK[DEFAULT_MODEL])
    return (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000.0


# --- .env loading (no external dependency) ----------------------------------


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a gitignored ``.env`` into os.environ.

    Existing environment variables win, so an explicitly exported key is never
    clobbered. Values are not logged. Best-effort: any parse error is ignored.
    """
    # repo root is two levels up from this file: cfa/ai/llm_client.py
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        # Never fail the caller because .env is unreadable; just run AI-off.
        return


def _get_api_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    _load_dotenv()
    return os.environ.get("OPENAI_API_KEY") or None


def _model() -> str:
    return os.environ.get("CFA_LLM_MODEL", DEFAULT_MODEL)


def ai_enabled() -> bool:
    """Return True when an OpenAI key is available (AI ON), else False.

    This lets a UI decide up front whether to offer an AI action or show a
    disabled control, *without* making a network call. It reflects only key
    presence — a live call may still fail (and fall back) for other reasons.
    The key itself is never returned or logged.
    """
    return _get_api_key() is not None


# --- in-app AI toggle (persisted in col.conf -> syncs natively) -------------
#
# The key-presence check above is necessary but not sufficient: a user with a
# key configured must still be able to turn AI OFF in the app, per-feature, and
# have that choice sync to the phone. That switch lives in the collection
# config (three keys, all default ON — AI-first; without a key the app is still
# deterministic), and the effective gate for any AI feature is:
#
#     ai_feature_enabled(feature) == key_present AND master AND feature
#
# These string constants are the single source of truth for the key names; the
# desktop toggle UI, the Kotlin client, and docs/cfa/AI-PROVENANCE.md all refer
# to them. `col` is duck-typed (only `.get_config(key, default)` is used) so
# this module stays free of any `anki` import and testable without a backend.

CONF_AI_MASTER = "cfa_ai_enabled"
CONF_AI_GRADING = "cfa_ai_grading_enabled"
CONF_AI_TABFILL = "cfa_ai_tabfill_enabled"

# Feature name -> its per-feature col.conf key.
AI_FEATURE_KEYS: dict[str, str] = {
    "grading": CONF_AI_GRADING,
    "tabfill": CONF_AI_TABFILL,
}


def key_present() -> bool:
    """True when an OpenAI key is configured (alias of :func:`ai_enabled`)."""
    return _get_api_key() is not None


def _read_conf(feature_key: str, col: object, conf: Optional[dict]) -> dict:
    """Resolve the master + per-feature toggle values from ``conf`` or ``col``.

    Missing keys default to True (AI-first): AI is ON unless explicitly turned
    off. Without an API key the feature still degrades deterministically."""
    if conf is not None:
        return conf
    if col is not None:
        get = col.get_config  # type: ignore[attr-defined]
        return {
            CONF_AI_MASTER: get(CONF_AI_MASTER, True),
            feature_key: get(feature_key, True),
        }
    return {}


def ai_feature_enabled(
    feature: str, *, col: object = None, conf: Optional[dict] = None
) -> bool:
    """Return True iff AI is enabled for ``feature``.

    The gate is ``key_present() AND master-switch AND per-feature-switch`` —
    all three must hold. Pass either a live ``col`` (its ``get_config`` is
    read) or a plain ``conf`` mapping (e.g. ``col.all_config()``); with neither,
    the switches default OFF. Unknown feature names raise ``ValueError`` so a
    typo can never silently read as "enabled".
    """
    if feature not in AI_FEATURE_KEYS:
        raise ValueError(
            f"unknown AI feature {feature!r}; expected one of "
            f"{sorted(AI_FEATURE_KEYS)}"
        )
    if not key_present():
        return False
    feature_key = AI_FEATURE_KEYS[feature]
    resolved = _read_conf(feature_key, col, conf)
    if not bool(resolved.get(CONF_AI_MASTER, True)):
        return False
    return bool(resolved.get(feature_key, True))


def ai_toggle_state(*, col: object = None, conf: Optional[dict] = None) -> dict:
    """Snapshot of every toggle, for an in-app settings panel / status line.

    Returns ``{"key_present", "master", "grading", "tabfill", "grading_on",
    "tabfill_on"}`` where the ``*_on`` values are the fully-resolved effective
    gates (what :func:`ai_feature_enabled` returns)."""
    if conf is None and col is not None:
        get = col.get_config  # type: ignore[attr-defined]
        conf = {
            CONF_AI_MASTER: get(CONF_AI_MASTER, True),
            CONF_AI_GRADING: get(CONF_AI_GRADING, True),
            CONF_AI_TABFILL: get(CONF_AI_TABFILL, True),
        }
    conf = conf or {}
    kp = key_present()
    master = bool(conf.get(CONF_AI_MASTER, True))
    grading = bool(conf.get(CONF_AI_GRADING, True))
    tabfill = bool(conf.get(CONF_AI_TABFILL, True))
    return {
        "key_present": kp,
        "master": master,
        "grading": grading,
        "tabfill": tabfill,
        "grading_on": kp and master and grading,
        "tabfill_on": kp and master and tabfill,
    }


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _result(
    *,
    ok: bool,
    text: str,
    model: str,
    purpose: str,
    usage: Optional[Usage] = None,
    error: Optional[str] = None,
) -> CompletionResult:
    return {
        "ok": ok,
        "text": text,
        "model": model,
        "usage": usage
        or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "error": error,
        "purpose": purpose,
    }


def complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 512,
    temperature: float = 0.0,
    timeout: float = 30.0,
    purpose: str = "unspecified",
) -> CompletionResult:
    """Run one chat completion. Never raises for operational failures.

    Returns a :class:`CompletionResult`. On any failure (no key, cost cap hit,
    network/rate-limit/timeout after retries) ``ok`` is False and ``error``
    holds a short structured code so callers can fall back deterministically.
    The API key is never included in the returned dict or the error string.
    """
    global _tokens_used, _cost_used_usd
    model = _model()

    key = _get_api_key()
    if not key:
        # AI OFF: this is the deterministic-fallback contract, not an error.
        return _result(
            ok=False, text="", model=model, purpose=purpose, error="no_api_key"
        )

    # Enforce the per-process cost/token cap *before* spending.
    max_tokens_cap = _int_env(
        "CFA_LLM_MAX_TOKENS_PER_PROCESS", DEFAULT_MAX_TOKENS_PER_PROCESS
    )
    max_cost_cap = _float_env("CFA_LLM_MAX_COST_USD", DEFAULT_MAX_COST_USD)
    with _lock:
        if _tokens_used >= max_tokens_cap or _cost_used_usd >= max_cost_cap:
            return _result(
                ok=False,
                text="",
                model=model,
                purpose=purpose,
                error="cost_cap_exceeded",
            )

    try:
        from openai import OpenAI
    except ImportError:
        return _result(
            ok=False, text="", model=model, purpose=purpose, error="openai_sdk_missing"
        )

    max_retries = _int_env("CFA_LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES)
    client = OpenAI(api_key=key, timeout=timeout, max_retries=0)

    last_error = "unknown_error"
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            raw = (resp.choices[0].message.content or "") if resp.choices else ""
            text = raw.strip()
            u = resp.usage
            usage: Usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
                "total_tokens": getattr(u, "total_tokens", 0) or 0,
            }
            cost = _estimate_cost_usd(
                model, usage["prompt_tokens"], usage["completion_tokens"]
            )
            with _lock:
                _tokens_used += usage["total_tokens"]
                _cost_used_usd += cost
            return _result(
                ok=True, text=text, model=model, purpose=purpose, usage=usage
            )
        except Exception as exc:  # noqa: BLE001 - normalize to a structured code
            last_error = _classify_error(exc)
            if attempt < max_retries and _is_retryable(exc):
                time.sleep(_RETRY_BASE_DELAY_S * (2**attempt))
                continue
            break

    return _result(ok=False, text="", model=model, purpose=purpose, error=last_error)


def _is_retryable(exc: Exception) -> bool:
    name = type(exc).__name__
    return name in {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "APIError",
    }


def _classify_error(exc: Exception) -> str:
    """Map an exception to a short, key-safe error code (no message leakage)."""
    name = type(exc).__name__
    mapping = {
        "AuthenticationError": "auth_error",
        "PermissionDeniedError": "permission_denied",
        "RateLimitError": "rate_limited",
        "APITimeoutError": "timeout",
        "APIConnectionError": "connection_error",
        "InternalServerError": "server_error",
        "BadRequestError": "bad_request",
        "NotFoundError": "model_not_found",
    }
    return mapping.get(name, f"api_error:{name}")


__all__ = [
    "complete",
    "ai_enabled",
    "key_present",
    "ai_feature_enabled",
    "ai_toggle_state",
    "CONF_AI_MASTER",
    "CONF_AI_GRADING",
    "CONF_AI_TABFILL",
    "AI_FEATURE_KEYS",
    "usage_so_far",
    "reset_usage",
    "CompletionResult",
    "DEFAULT_MODEL",
]
