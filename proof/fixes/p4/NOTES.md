# ankiCFA — P4: Engineering-Quality Gaps & Submission Proof — NOTES

Owner: **P4** workstream. Every increment is additive, evidence-first, and gated via `no-mistakes`.

Scope owned: `.env` / `.env.example` / `.gitignore`; mypy/type fixes in non-Qt CFA files
(`tools/cfa/sync_roundtrip.py`, `pylib/anki/cfa_sync.py`, mypy path config); the aqt test
PYTHONPATH wiring; `cfa/ai/*` and `cfa/ethics_pairs/eval_*` with-key proof; `proof/` & `demo/`
artifacts.

Not owned (do **not** edit): `qt/aqt/cfa.py` & `pylib/anki/cfa.py` (P1), `docs/` (P3),
the AnkiDroid repo (P2). Residual mypy errors in P1 files are flagged here, not fixed.

---

## Item 1 — Key hygiene (SECURITY)

- Branch: `p4/01-key-hygiene` (off `origin/main` @ `557a7cc82`)
- Commit SHA: _recorded via `git log` on the branch_
- Gate (no-mistakes): _outcome + PR link appended after the run_

What was found / done (additive):

- Verified the real `OPENAI_API_KEY` lives ONLY in the gitignored, untracked `.env`.
  `git check-ignore .env` passes; `.env` is neither tracked nor staged.
- `.env.example` holds the placeholder `OPENAI_API_KEY=sk-your-key-here` (no real key).
- Strict grep `sk-(proj-)?[A-Za-z0-9_-]{20,}` over tracked files returns only TWO matches,
  both the intentional fake fixture `sk-should-never-appear-in-prompt` in
  `cfa/ethics_pairs/tests/test_ai_grading.py` — the redaction test
  `test_prompt_includes_evidence_and_never_the_key`, which proves the real key is never sent
  to the LLM. Excluding that test file → **ZERO** matches, proving no real key is tracked.
  The security test was intentionally left intact (documented, not weakened).
- Hardening: extended `.gitignore` to also ignore `.env.*` variants (e.g. `.env.local`,
  `.env.withkey.bak`) while keeping `.env.example` tracked — this prevents accidentally
  committing key-bearing backups, notably the `.env.withkey.bak` the Item 4 with-key proof
  creates when it exercises the AI-off fallback.

Evidence:

- Before: `proof/fixes/p4/1-keyhygiene-before.txt`
- After:  `proof/fixes/p4/1-keyhygiene-after.txt`

Verify (AI-off unaffected): no application code changed — only `.gitignore` + proof files.

<!-- Subsequent items (2–5) append their entries below. -->
