# ankiCFA — Native CFA Level II Product Spec (Phase-0 contract)

This is the contract the worker tabs (W1–W6) build against. It is owned by the
Phase-0 spine and is the place interface questions are answered — **edit this
doc, not another tab's files.** Companion contracts:
[AI-PROVENANCE.md](AI-PROVENANCE.md) (AI toggle + provenance),
[SYNC-SETUP.md](SYNC-SETUP.md) (two-way sync harness).

## 0. What we are building

A **native CFA Level II prep product**, not "Anki with a CFA menu." The app
*is* a CFA study tool: it boots into a CFA Home dashboard, it is branded
ankiCFA, its flagship study modes are CFA-specific (minimal-pairs ethics,
exam-priority queue, deadline/peak-on-exam-day, readiness), and desktop and
mobile read identical numbers from one shared Rust engine.

Hard rules (never violate): **additive only** — never break sync, FSRS
scheduling, or undo; **never commit the API key**; desktop ⇄ mobile parity;
default model **GPT-4o**.

## 1. Branding

- **Name:** ankiCFA (window title, about box, launcher).
- **Icon:** CFA-marked app/toolbar icon (W2 owns the asset).
- **Toolbar / primary nav:** `Home · Study · Ethics · Readiness · Sync`.
  Same five destinations on desktop and mobile (mobile may render them in the
  nav drawer / bottom bar).

## 2. CFA Home dashboard (the boot surface)

The app opens on **CFA Home**, not the stock Anki deck browser. Home is a
read-only dashboard whose single data source is the shared engine (§4):

- **Three honest scores**, each shown as a **range** (never a bare number) with
  its give-up state: **Memory** (exam-weighted FSRS retrievability ± spread),
  **Performance** (first-exposure Wilson 95%), **Readiness** (wide logistic
  P(pass), carrying the standing caveat *"not validated against real exam
  data"*). When a score abstains, Home shows its `reason` string verbatim
  ("not enough data: …") — abstention is a feature, not an error.
- **Bayesian readiness "hero"** — the headline band that *never* abstains:
  accuracy point + 95% credible band + an explicit `likely pass` / `likely
  fail` call with its probability, narrowing as evidence accrues.
- **Days to exam** (from the persisted exam config) and entry points to
  **Study** (exam-priority queue), **Ethics** (minimal-pairs), **Readiness**
  (deadline / peak-on-exam-day), and **Sync**.

Every number on Home is a field of the `ComputeCfaScores` response — Home does
no statistics of its own.

## 3. Ethics = minimal-pairs (flagship); retire one-passage

The flagship ethics mode is **minimal-pairs** (`cfa/ethics_pairs/`): near-identical
scenario pairs that differ by one decision-relevant fact, forcing discrimination
of the governing Standard. The legacy **one-passage** ethics card is **retired** —
remove it from the seeded deck and stop referencing it in docs/tests (W-hygiene
owns the retirement sweep). Ethics AI grading (semantic highlight grading) must
work on the minimal-pairs flow and degrade to the deterministic grader when AI
is off (see AI-PROVENANCE.md).

## 4. Shared score engine — `ComputeCfaScores` RPC  ✅ shipped in Phase-0

One engine, in Rust, computes all four honest scores; desktop (`anki.cfa`) and
mobile (`col.backend.computeCfaScores`) both call it, so the numbers are
computed in exactly one place.

**Proto** (`proto/anki/scheduler.proto`, `SchedulerService`):

```proto
rpc ComputeCfaScores(ComputeCfaScoresRequest) returns (ComputeCfaScoresResponse);

message ComputeCfaScoresRequest {
  int64 deck_id = 1;          // deck (subdecks included)
  bool  whole_collection = 2; // true => score everything, deck_id ignored
  int64 now = 3;              // unix secs; 0 => backend clock (tests pin it)
}
message ComputeCfaScoresResponse {
  CfaMemoryScore     memory     = 1;  // abstain/reason/point/range±/coverage/topics[]
  CfaPerformanceScore performance = 2; // abstain/reason/point/range±/first_exposures/correct
  CfaReadinessScore  readiness  = 3;  // abstain/reason/point/range±/label/inputs
  CfaBayesianReadiness bayesian = 4;  // accuracy/ci±/call/call_prob/p_pass/mps/recall/topics[]
}
```

All numeric fields are `double` (f64) to preserve exact parity with Python.
Weights + exam date come from `col.conf["cfa_exam_config"]` (already synced) —
they are **not** passed in the request, so one call reproduces `cfa.py` verbatim.

**Guarantees (verified in-tree):**
- **Parity:** the Rust engine equals the Python reference `anki.cfa._py_*`
  field-by-field to **1e-9** (`just cfa-parity-test`) — so desktop == mobile ==
  old Python.
- **Double-count fix:** graded reviews are counted **at most once per (card,
  day)**, so an offline dual-device round-trip cannot inflate the evidence
  (tested; `just cfa-parity-test`, and the Rust unit tests).
- **Read-only:** never writes a card/queue/scheduling row — FSRS + undo stay valid.
- `anki.cfa` public functions are **thin wrappers** over the RPC (with the
  pure-Python `_py_*` kept as reference + a fallback for an older backend).

**Desktop (Python):** `anki.cfa.memory_score(col, deck_id=…)` etc. return the
existing dataclasses, now sourced from the RPC.

**Mobile (Kotlin):** the binding `col.backend.computeCfaScores(...)` is
auto-generated into `GeneratedBackend.kt` when the AAR is rebuilt from this fork
(`Anki-Android-Backend/cfa_build_fork_engine.sh`). Wire it in the existing seam
`CfaScoresProvider.scores(col)` (which already exposes `rpcAvailable()` and a
`SOURCE_RPC`/`SOURCE_FALLBACK` marker) and map the response into `CfaScores`.
This wiring lands at integration, after Phase-0 merges (the AAR must be rebuilt
from merged `main` first). **D6** = the phone Home showing the three scores with
ranges + give-up.

## 5. AI + provenance + sync

See [AI-PROVENANCE.md](AI-PROVENANCE.md): AI is off by default, gated by three
`col.conf` keys (master + per-feature + key-present), every AI feature has a
deterministic fallback, and AI touches *content* only — the scores are always
deterministic (**D3**). See [SYNC-SETUP.md](SYNC-SETUP.md) for the real
two-way-sync harness (**D4/D5**).

## 6. Worker coordination & merge rules

- **Branches:** each worker pushes `friday/<name>`. The Phase-0 spine is
  `friday/phase0`.
- **Merge order:** `Phase0 → W2 → W3 → W1 / W4 / W5 / W6`. Phase-0 first because
  W1 (Home/desktop shell) and W4 (mobile scores) depend on the RPC.
- **Rebase before merge:** rebase each branch onto the latest target and resolve
  conflicts on the branch; keep the history additive.
- **Green gate:** `just check` (build + lint + tests) must stay green at every
  merge. CFA suites (`just cfa-parity-test cfa-scores-test cfa-f4-test
  cfa-ai-toggle-test cfa-types-test`) must pass **with AI OFF** (move `.env`
  aside during test runs).
- **Isolation:** the desktop tree is edited by multiple tabs concurrently. Work
  on your own branch/worktree; do **not** edit another tab's files. Interface
  questions are answered by editing *this* doc, not by reaching into a worker's
  code.

## 7. Acceptance (D1–D7) — see `proof/friday/ACCEPTANCE.md`

D1 AI names a source (provenance) · D2 eval-before-serve gate at 0.80 · D3
deterministic scores AI-off + in-app toggle · D4 real two-way sync round-trip,
no double-count · D5 offline-then-sync · D6 phone shows the 3 scores w/ ranges +
give-up · D7 eval numbers + phone→desktop recording · plus fresh-seed
reachability on desktop **and** mobile.
