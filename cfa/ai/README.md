# CFA AI foundation (`cfa/ai`)

A single reusable OpenAI client that every CFA AI feature (ethics grading,
tab-to-fill card backs, …) routes through. It is built around one hard rule:

> **Every AI feature MUST work fully with AI OFF via a deterministic fallback.**

## The AI-off contract

`complete()` **never raises** for an operational problem. It always returns a
result dict; the `ok` field is the only thing callers branch on:

```python
from cfa.ai.llm_client import complete

r = complete(system="You grade CFA ethics answers.",
             user="...",
             max_tokens=200,
             temperature=0.0,
             purpose="grade_ethics")

if r["ok"]:
    use(r["text"])          # AI ON
else:
    deterministic_fallback()  # AI OFF — no key, cost cap, or transient error
```

Result shape:

```python
{
  "ok": bool,
  "text": str,                 # "" when ok is False
  "model": str,                # model actually requested
  "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
  "error": str | None,         # short structured code when ok is False
  "purpose": str,
}
```

`error` codes include: `no_api_key`, `cost_cap_exceeded`, `openai_sdk_missing`,
`auth_error`, `rate_limited`, `timeout`, `connection_error`, `server_error`,
`bad_request`, `model_not_found`, `api_error:<Name>`.

## Setup

1. Install the dependency into the dev pyenv:

   ```sh
   out/pyenv/bin/python -m pip install -r cfa/ai/requirements.txt
   ```

2. Turn AI **on** by creating a local `.env` (gitignored) from the template:

   ```sh
   cp .env.example .env
   # edit .env and set OPENAI_API_KEY=sk-...
   ```

   With no key present, everything still works — AI-off.

## Configuration

All optional, read from the environment or the gitignored `.env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | Turns AI on. Absent → AI off (`ok=False`). |
| `CFA_LLM_MODEL` | `gpt-4o-mini` | Model override. |
| `CFA_LLM_MAX_TOKENS_PER_PROCESS` | `200000` | Cumulative token cap. |
| `CFA_LLM_MAX_COST_USD` | `1.00` | Cumulative USD cap. |
| `CFA_LLM_MAX_RETRIES` | `2` | Transient-error retries (exponential backoff). |

## Cost cap

The client tracks cumulative tokens and an **estimated** USD cost per process
(from published list prices — a local guardrail, not a billed amount). Once
either the token cap or the cost cap is reached, further calls return
`{ok: False, error: "cost_cap_exceeded"}` so a runaway loop cannot spend
unbounded money. Inspect the running total with `usage_so_far()`.

## Privacy

- The API key is **never** logged, printed, or included in any returned value
  or error string.
- Prompt/response content is sent to OpenAI only when AI is on. With AI off,
  nothing leaves the machine.
- `.env` is gitignored so the key is never committed.

## Smoke test

```sh
just cfa-ai-smoke
```

Covers **both** paths: the no-key path always runs and asserts a graceful
`ok=False`; the with-key path makes one tiny real call and asserts `ok=True`,
and is skipped automatically when no key is configured.
