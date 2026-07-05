# UI Critique Log — Phase B (multi-pass, both apps)

Process: SPEEDRUN-PLAN §4. Inventory (`UI-INVENTORY.md`) → capture → critique
against the rubric → log every issue with severity → fix all blocker+major →
re-capture + re-critique (harsher each pass). ≥3 passes per app.

**Rubric:** visual hierarchy; spacing/alignment/grid; typography scale; color,
contrast, WCAG AA; consistency & design-token use; affordances & discoverability;
microcopy; motion; empty/loading/error states; information density; functional
correctness; "does this look like a premium paid CFA-prep product."

**Critic-tooling honesty note.** The plan specifies GPT-4o vision as the CRITIC.
There is **no `OPENAI_API_KEY` / `.env`** available in this environment (verified
`env | grep OPENAI` empty, no `.env` file), so the automated GPT-4o vision leg is
**UNAVAILABLE** this run. Rather than fabricate a model transcript (honesty rule),
each pass below is a **structured senior-designer heuristic critique** performed
against the same rubric on the real captured screenshots, clearly labelled as
such. If a key is later provided, the same screenshots can be re-scored by GPT-4o
without recapture.

Severity: **BLOCKER** (broken / ships-embarrassing) · **MAJOR** (clearly
sub-premium, must fix) · **MINOR** (polish).

---

## Pass 1 — DESKTOP (critical)

Captures (before/after pairs from `ts/tests/e2e/cfa_readiness_render.test.ts`,
`CFA_UI_OUT` override):
- `desktop-ui/pass-1-before/` — pre-fix renders.
- `desktop-ui/pass-1/` — post-fix renders (current).
  - `01-cfa-home.png` — CFA Home (D1), first-run/abstain, real CFA Level II deck.
  - `02-cfa-readiness.png` — Exam Readiness (D2), real deck, abstain + coverage map.
  - `03-cfa-readiness-empty-deck.png` — Readiness (D2) for the empty Default deck.

**Fixes applied this pass (re-captured + re-verified, tests green):**
- **D1-2 / D2-2 FIXED (MAJOR — hierarchy inversion / abstain shouts)** — the
  three StatCards no longer render "Not enough data" as a huge warn-orange serif.
  On abstain they now show a **quiet, down-sized muted-grey "Awaiting reviews"**
  (`bandValue` → "Awaiting reviews", `bandTone` → new `muted` tone = `$cfa-faint`
  at subtitle 22px, not the 40px display), with the give-up reason in the faint
  sub-line. The "not enough data — keep studying" verdict is now stated **exactly
  once**, in the Readiness hero — so absence never out-weighs the countdown, the
  real numbers, or the CTAs. (before `pass-1-before/` → after `pass-1/`.)
- **D1-1 / D2-1 FIXED (MAJOR — StatCard dead space)** — with the abstain value
  down-sized to a short one/two-word line (not a 4-line wrapping headline) the
  three cards are consistent and the padded/empty look is gone.
- **D1-3 FIXED (MAJOR — color-semantic collision)** — abstain scores are now
  `muted` grey, so the warn-orange hue no longer doubles as both "warning" and
  sits beside the peach primary CTA. Additionally the **unset-exam countdown**
  (`examCountdown`, Home first-run) is now `neutral` navy rather than `warn`, so
  the warm **primary CTA is the single accent** that leads the eye and orange is
  reserved for a genuinely near deadline (≤14 days).
- **D2-3 FIXED** — `captionText` now omits the "as of …" clause when there is no
  last-review timestamp, so the caption ends cleanly at "… 0 first-seen" instead
  of the unfinished-looking "· as of —". (before `pass-1-before/02` → after
  `pass-1/02`.)
- **D2-4 FIXED** — `topicRows` now sorts with a deterministic secondary key
  (topic name) so equal-weight areas render in a stable, scannable order
  (Equity → Ethics → Financial Reporting → Fixed Income → Portfolio for the five
  0.12 areas) rather than an arbitrary tiebreak.
- Drive-by: un-nested a pre-existing `no-nested-ternary` eslint failure in
  `home.ts` (D1 headline) so the desktop lint gate (`check:eslint`, svelte, tsc)
  is fully green.

**Functional gate (named must-fix "Readiness does nothing"):** RESOLVED +
regression-guarded. `ts/tests/e2e/cfa_readiness_render.test.ts` (3 tests, green)
boots the real backend and asserts `/cfa-readiness/{deckId}` and `/cfa-home`
render the three honest scores, the honest hero, and the full **per-topic
coverage map** (all 10 canonical CFA areas + real exam weights) bound to real
backend data — plus the empty-deck path renders without a blank screen. The
Readiness screen demonstrably opens and renders with real data.

### D1 — CFA Home
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D1-1 | MAJOR | 3 score cards | On abstain the cards have large dead vertical space below the give-up text; card heights look padded/empty and the third card wraps to 4 lines while the first two are short — inconsistent internal density. | **FIXED** — abstain value down-sized to a short one/two-word "Awaiting reviews" (not a 4-line headline); cards now consistent. |
| D1-2 | MAJOR | "Not enough data" ×3 | The empty-state headline renders as a huge warn-orange serif three times, dominating the page above the exam countdown — hierarchy inversion (the loudest thing is the *absence* of data). | **FIXED** — abstain value is now a quiet, down-sized (22px) muted-grey "Awaiting reviews" with the reason in the faint sub; the verdict is said once in the hero. |
| D1-3 | MAJOR | peach "Ethics" CTA vs warn-orange | The highlighted primary CTA (peach) shares the warn/orange family used by "Not enough data", so the same hue reads as both "primary action" and "warning" — semantic color collision. | **FIXED** — abstain now uses the `muted` grey tone (not warn); unset-exam countdown is now neutral navy so the peach CTA is the single warm accent. |
| D1-4 | MINOR | study CTA grid | 3-then-2 card grid leaves an empty cell on the right of row 2 — asymmetric. | Balance to a 2×? or center the trailing row / promote a 5th tile. |
| D1-5 | MINOR | AI pill vs "Browse decks →" | Two footer controls use inconsistent affordances (outline pill vs text-link-with-arrow). | Unify into one control style (both pills, or both links). |
| D1-6 | MINOR | footer paragraph | Long, low-contrast methodology paragraph; dense first-run microcopy. | Collapse behind a "How scores work" disclosure or trim. |

### D2 — Exam Readiness
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D2-1 | MAJOR | 3 score cards | Same dead vertical space as D1-1 (cards sized for value+range, abstain text short). | **FIXED** — shared StatCard down-sized abstain value (same `bandValue`/`muted` fix as D1-1). |
| D2-2 | MAJOR | hero + 3 cards | "Not enough data" appears 4× in loud orange on one screen (hero + 3 cards) — repetitive and alarmist for a normal first-run. | **FIXED** — said **once** in the hero; the 3 cards now show a quiet muted "Awaiting reviews" (verified in `pass-1/02`). |
| D2-3 | MINOR | coverage caption | "as of —" renders an em-dash placeholder → looks unfinished. | **FIXED** — clause omitted when no timestamp (`captionText`). |
| D2-4 | MINOR | per-topic table sort | The five 0.12-weight areas are not in a stable/canonical order (arbitrary tiebreak). | **FIXED** — deterministic secondary sort by topic name (`topicRows`). |
| D2-5 | MINOR | 10 identical "no data" rows | Honest but visually flat empty table. | A single-line "No reviews yet — recall appears here after you study" hint above/within the table. |

**Pass-1 desktop verdict:** the CFA web surfaces are already close to premium
(brand serif lockup, calm palette, real coverage map). The dominant real defects
were (a) abstain-state hierarchy — the empty state shouted in warn-orange and
out-weighted the countdown/CTAs (D1-2, D2-2), and (b) StatCard dead space +
color-semantic collision (D1-1/D2-1, D1-3). **All five Pass-1 desktop MAJORs are
now FIXED, re-captured (`pass-1/`), and re-verified** (`test-e2e` 6/6 green,
`check:eslint`/svelte/tsc green) — the abstain state is now a calm muted-grey
"Awaiting reviews" with the verdict stated once in the hero, and the peach
primary CTA is the single warm accent that leads the eye. Remaining Pass-1
desktop items are MINORs (D1-4/5/6, D2-5) + surfaces not yet captured this run:
D3 Deadline, D4 Ethics reviewer, D6 AI Settings, D7 Connect/Logout, D8 deck
browser, D11 chrome (Qt surfaces) + a populated (non-abstain) render of D1/D2.

### Still-TODO (desktop, later this pass / next)
- Populated (real ranges + Bayesian pass/fail call) capture of D1/D2 — needs a
  reviewed collection; the Python payload path is already unit-tested (F4 /
  `bayesian_readiness`), the web render capture is pending.
- Qt-chrome surfaces (D5–D8, D10–D12) via `screencapture`/`grab()`.

---

## Pass 1 — MOBILE (critical) — TODO
Captures pending under `proof/friday/gnhf-speedrun/mobile-ui/pass-1/`. Some
device renders already exist from Phase A (M1–M5 under `AnkiDroid:
proof/gnhf-speedrun/L3/`) and will be re-shot under the Phase-B rubric.

## Pass 2 (harsher) — TODO (both apps)
## Pass 3 (ruthless, pixel-level) — TODO (both apps)
