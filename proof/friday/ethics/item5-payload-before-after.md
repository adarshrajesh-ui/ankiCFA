# INC5 — attempt-detail payload: before → after

The minimal-pair FRONT card persists a grade payload to `localStorage["cfaEthics:pending"]` on a
completed attempt (and relays it via `pycmd`), which the BACK reads and which W5 will store in
`card.custom_data` (syncs).

## BEFORE (original `front.html`, single-phrase card)

The payload was minimal — just enough to auto-rate:

```js
var grade = {
    pairId: pairId,
    cluster: cluster,
    correct: root.dataset.correct === "1",
};
localStorage.setItem("cfaEthics:pending", JSON.stringify(grade));
```

i.e. `{ pairId, cluster, correct }` — no verdicts, no highlight spans, no per-span tiers, no grade
tier, no source/standard provenance. W5 could persist only pass/fail.

## AFTER (multi-span flagship, this workstream)

The card emits the full structured attempt detail the moment Check reveals the grade (see
`front.html` `reveal()` → `pendingGrade`), and upgrades `source` to `"ai"` in place if the desktop
AI bridge returns an `ai` grade. Verified by driving the REAL card in headless Chrome and reading
`localStorage["cfaEthics:pending"]` — see `item5-emitted-payload.json` (captured live) and the two
passing tests in `cfa/ethics_pairs/tests/test_attempt_payload.py`.

Shape (verbatim keys emitted):

```
pairId, itemId, cluster, completed, correct, standard, rationale, source,
verdicts: { A:{judged,answer,ok}, B:{judged,answer,ok} },
decisiveCase, highlight (correct|somewhat|partial|wrong), found, near, total,
selectionIndices: [int...],   // union of token indices highlighted in the decisive vignette
spans: [ { phrase, rationale, tier (full|near|none), matched, lo, hi } ]   // lo/hi = gold span token range
```

The exact contract + W5 persistence guidance is documented in `HANDOFF.md` (→ W5).
