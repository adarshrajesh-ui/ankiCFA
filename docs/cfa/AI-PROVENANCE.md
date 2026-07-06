# CFA AI Provenance & Toggle Contract

Every AI-touched item in ankiCFA must be able to say **where its content came
from**, and every AI feature must be individually switch-off-able and work fully
with AI OFF via a deterministic fallback. This document is the single source of
truth both the desktop and mobile clients build against.

## Provenance record

Whenever an AI feature produces (or declines to produce) content — a graded
ethics highlight, a tab-filled answer, a generated explanation — it attaches a
provenance record so the UI can badge it and a reviewer can audit it:

```json
{
  "source": "ai" | "fallback",
  "standard": "III(A)",
  "item_id": "ethics::los::soft-dollars::0007",
  "model": "gpt-4o",
  "rationale": "Client brokerage (soft dollars) must benefit the client; …"
}
```

| field       | type                   | meaning                                                                                                                                                      |
| ----------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `source`    | `"ai"` \| `"fallback"` | `ai` = a live model call succeeded and was used; `fallback` = the deterministic no-network path produced it (no key, AI off, cost cap, error). **Required.** |
| `standard`  | string                 | The CFA Standard / LOS the item is about (e.g. `III(A)`), or `""` if not applicable.                                                                         |
| `item_id`   | string                 | Stable id of the item this record describes (card/note key or ethics-pair id) so records can be joined back to content. **Required.**                        |
| `model`     | string                 | Model id used when `source=="ai"` (e.g. `gpt-4o`); `""` for `fallback`.                                                                                      |
| `rationale` | string                 | Short human-readable justification/explanation shown to the learner and kept for audit. Never contains the API key.                                          |

Rules:

- `source=="fallback"` ⟹ `model==""`. `source=="ai"` ⟹ `model` is set.
- The record is **content**, not a secret: it may be stored on the note / synced.
  The API key never appears in any field or log.
- The default model is **GPT-4o** (`gpt-4o`), set via `CFA_LLM_MODEL`. (The legacy
  default was `gpt-4o-mini`; product target is GPT-4o.)

## The in-app AI toggle (`col.conf` keys)

AI is **off by default** and gated by three collection-config keys, which sync
natively with the collection (so a choice made on desktop reaches the phone).
Defined in `cfa/ai/llm_client.py`:

| key                      | default | meaning                                                       |
| ------------------------ | ------- | ------------------------------------------------------------- |
| `cfa_ai_enabled`         | `false` | **master** switch — off ⟹ all AI off regardless of the others |
| `cfa_ai_grading_enabled` | `false` | ethics semantic-grading feature                               |
| `cfa_ai_tabfill_enabled` | `false` | tab-to-fill feature                                           |

The effective gate for a feature is the **AND of three conditions**:

```
ai_feature_enabled(feature) ==
    key_present()                    # an OpenAI key is configured
    AND col.conf[cfa_ai_enabled]     # master switch on
    AND col.conf[<per-feature key>]  # that feature's switch on
```

Call it from feature code:

```python
from cfa.ai import llm_client
if llm_client.ai_feature_enabled("grading", col=col):
    ... # try the model; on any failure, fall back deterministically
else:
    ... # deterministic path (always available)
```

`llm_client.ai_toggle_state(col=col)` returns the full snapshot
(`key_present`, `master`, per-feature, and the resolved `*_on` gates) for an
in-app settings panel / status line. `col` is duck-typed — only `get_config`
is read — so the gate is testable without a backend (`just cfa-ai-toggle-test`).

## Consequence for scoring (determinism)

The honest scores (`ComputeCfaScores` / `anki.cfa`) contain **no AI** — pure
spaced-repetition statistics — so with AI off the three scores and the Bayesian
band are fully deterministic (acceptance **D3**). AI only ever augments _content_
(grading, tab-fill, explanations), never the numbers.
