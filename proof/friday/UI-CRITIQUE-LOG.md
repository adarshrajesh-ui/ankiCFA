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

## Pass 1 — MOBILE (critical)

Captures live in the **mobile repo** (branch `gnhf/speedrun-mobile`) at
`AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-1-before/` (device `emulator-5554`,
`adb screencap`, real running debug build):
- `01-deckpicker.png` — native ankiCFA DeckPicker (landing).
- `02-nav-drawer.png` — nav drawer (Exam Readiness / Decks / Card browser…).
- `03-exam-readiness.png` — Exam Readiness top (hero + 3 score cards, abstain).
- `04-exam-readiness-bottom.png` — Readiness per-topic recall + action buttons.
- `05-exam-config.png` — Exam configuration (no date set).
- `06-reviewer-question.png` — Reviewer, question side (CFA card).
- `07-reviewer-answer.png` — Reviewer, answer side + ease buttons.

Same honesty caveat as desktop: **no `OPENAI_API_KEY`**, so this is a labelled
structured senior-designer heuristic critique on the real device captures, not a
GPT-4o transcript. Every issue is grounded in a specific screenshot + source
line so a Pass-2 fix is unambiguous.

**Headline finding (matches the objective's "non-native-CFA feel" + "full
AnkiDroid CFA UI refactor is the biggest lift"):** the CFA *activities* (Exam
Readiness / Config) carry the navy+orange brand, but the **shell the user
actually lives in — DeckPicker, nav drawer, and Reviewer — is 100% stock
AnkiDroid light-blue**, so the product reads as "AnkiDroid with two bolt-on CFA
screens," not a native CFA app. Two mobile MAJORs are the *same* defects already
fixed on desktop (abstain shouts in warn-orange; brand accent == warn colour).

### M1 — DeckPicker (landing shell)
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M1-1 | MAJOR | toolbar + status bar | Stock AnkiDroid light-blue (`#0a9beb`) toolbar/status bar on the primary landing screen — clashes with the navy CFA activities; app doesn't feel like a CFA product on first open. | Theme the DeckPicker action bar + status bar to `cfa_navy`; make navy the shell primary. |
| M1-2 | MAJOR | deck list | Junk test decks **"h"** and **"h gg"** shipped in the collection — embarrassing leftover data on a premium product. | Purge non-CFA scratch decks from the seeded/synced collection; default list = CFA / Ethics Pairs / CFA Level II only. |
| M1-3 | MINOR | FAB + no CFA entry | The `+` FAB and sync icon are stock blue; Exam Readiness (the flagship CFA surface) is buried in the drawer with no DeckPicker entry point. | Recolour FAB to `cfa_accent`; consider a persistent "Exam Readiness" CTA on DeckPicker. |

### M2 — Nav drawer
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M2-1 | MAJOR | drawer header | Header is the stock AnkiDroid blue mountain illustration — no CFA logo/wordmark; active item "Decks" highlighted in AnkiDroid blue, not a CFA token. | Replace header with a CFA navy brand lockup; recolour the selected-item accent to `cfa_accent`/`cfa_navy`. |
| M2-2 | MINOR | icons + labels | "Exam Readiness" uses the same generic bar-chart glyph as "Statistics"; "Support AnkiDroid" reads as upstream, not the product. | Give Exam Readiness a distinct CFA icon; ensure brand consistency of drawer labels. |

### M3 — Exam Readiness (flagship CFA screen)
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M3-1 | MAJOR | 3 score values | "N/A — abstaining" renders **3× in loud warn-orange** (`CfaExamReadinessActivity.kt:177` → `cfa_warn`) — hierarchy inversion; the *absence* of data is the loudest thing on screen. **Identical to desktop D1-2/D2-2 (already fixed there).** | **FIXED (iter 28)** — abstain is now a calm muted-grey "Awaiting reviews" (`cfa_muted`, non-bold, down-sized 22/18sp) with the give-up reason in the faint sub-line; verified `pass-1/03-exam-readiness.png`. |
| M3-2 | MAJOR | brand eyebrow vs abstain | The orange brand eyebrow "ANKICFA · CFA LEVEL II" is the same warm-orange family as the warn/abstain text → brand accent == warning (colour-semantic collision). **Desktop D1-3 parallel.** | **FIXED (iter 28)** — abstain moved off the warm hue to grey `cfa_muted`, so the orange brand eyebrow is now the single warm accent; `cfa_warn` is reserved for a genuine near-deadline warning (currently unused). |
| M3-3 | MAJOR | 3 score "cards" | Inconsistent card treatment — Readiness sits in a grey filled card (`cfa_surface`) while Memory/Performance are flat/borderless; they aren't consistent cards. | **FIXED (iter 28)** — all three cards now share one container (`drawable/cfa_score_card_bg`: `cfa_surface` fill + `cfa_line` hairline stroke + 12dp radius); the hero is emphasised only by its larger value text. Verified `pass-1/03`. |
| M3-4 | MINOR | status bar | Light-blue status bar sits above the navy toolbar → two-tone band at the very top. | Set the status-bar colour to `cfa_navy` for CFA activities. |
| M3-5 | MINOR | per-topic table | 8 flat "no data" rows, no empty-state hint line (desktop D2-5 parallel). Shows **8** canonical topics vs desktop's **10** (known, documented parity gap — the AAR is built from `main`). | Add a one-line "recall appears here after you study" hint; extend to 10 topics when the fork AAR is rebuilt. |
| M3-6 | MINOR | outlined button | "Exam configuration" outlined-button label is AnkiDroid blue, off-brand. | **FIXED (iter 28)** — new `Widget.Cfa.Button.Outlined` style (navy label + navy stroke + accent ripple) applied to the "Exam configuration" button; verified `pass-1/04`. |

### M4 — Exam Config
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M4-1 | MAJOR | "Pick date" button | Outlined-button label is AnkiDroid blue (off-brand) — same token gap as M3-6; every outlined button across CFA screens inherits the Material default accent instead of a CFA token. | **FIXED (iter 28)** — the shared `Widget.Cfa.Button.Outlined` style (navy label + stroke) is applied to the "Pick date" button too; verified `pass-1/05-exam-config.png` (matches the navy "Save" button). |
| M4-2 | MINOR | layout density | Large dead vertical space; sparse screen (title + one field + 2 buttons), no context on why the exam date matters. | Add a short helper line; tighten layout or add a countdown preview. |

### M5 — Reviewer (highest-time-on-screen surface)
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M5-1 | MAJOR | whole chrome | Reviewer is 100% stock AnkiDroid: light-blue toolbar, light-blue "99 1 0" count bar, default ease-button colours — zero CFA identity on the screen users spend the most time on. | Theme reviewer toolbar/count bar to CFA navy; align typography with the CFA design system. |
| M5-2 | MINOR | ease buttons | Stock red/grey/green/blue ease bar; count-bar background light-blue. | Optionally align ease palette to the CFA system while keeping the four-grade semantics. |

**Pass-1 mobile verdict:** the two dedicated CFA activities are close to the
desktop bar in *structure* (brand eyebrow, navy title, honest score cards, real
per-topic recall) but repeat desktop's two worst defects (M3-1 abstain-shouts,
M3-2 accent==warn) and — more importantly — the **shell around them is
un-branded stock AnkiDroid** (M1-1, M2-1, M5-1). **7 MAJORs** logged (M1-1, M1-2,
M2-1, M3-1, M3-2, M3-3, M4-1, M5-1 — note M4-1 is the shared outlined-button
token) plus 8 MINORs. These become the Pass-2 mobile fix backlog (the "full
AnkiDroid CFA UI refactor" the objective flags as the biggest lift). No BLOCKERs
(every screen renders correct, honest data).

**Fixes applied (iter 28) — the 4 CFA-activity MAJORs:** M3-1 (abstain shouts),
M3-2 (accent==warn), M3-3 (inconsistent cards), and M4-1/M3-6 (off-brand
outlined buttons) are **FIXED, re-captured (`mobile-ui/pass-1/`), and re-verified**
(`ktlintCheck` + `lintVitalFullRelease` + CFA unit tests all green). The abstain
state is now a calm muted-grey "Awaiting reviews", all three score cards share one
rounded surface container, and the CFA outlined buttons use a navy token style.
This mirrors the desktop iter-26 abstain fix on mobile.

**Still-open mobile MAJORs (Pass-2 backlog — the shell refactor):** M1-1
(DeckPicker toolbar/status bar stock blue), M1-2 (junk scratch decks "h"/"h gg"),
M2-1 (nav-drawer header stock-blue mountain), M5-1 (Reviewer chrome 100% stock
AnkiDroid). These are the "non-native-CFA feel" the objective flags and are the
biggest remaining lift because they touch the shared AnkiDroid shell theme, not
bolt-on CFA activities.

## Pass 2 (harsher) — TODO (both apps)
## Pass 3 (ruthless, pixel-level) — TODO (both apps)
