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
| D1-4 | MINOR | study CTA grid | 3-then-2 card grid leaves an empty cell on the right of row 2 — asymmetric. | **FIXED (iter 30)** — the flagship primary "Study Ethics" CTA now spans the full width (`grid-column: 1/-1`) as a featured tile and the remaining four form a clean, symmetric 2×2 (`repeat(2, minmax(0,1fr))`, collapses to 1 col ≤560px); no orphaned cell. Verified `pass-1/01`. |
| D1-5 | MINOR | AI pill vs "Browse decks →" | Two footer controls use inconsistent affordances (outline pill vs text-link-with-arrow). | **FIXED (iter 30)** — both footer controls are now ONE pill affordance (`cfa-home__chip`); the "→" arrow was dropped from "Browse decks" so there is no mixed pill-vs-text-link treatment. Verified `pass-1/01`. |
| D1-6 | MINOR | footer paragraph | Long, low-contrast methodology paragraph; dense first-run microcopy. | **FIXED (iter 30)** — the dense methodology paragraph is collapsed behind a quiet `<details>` disclosure ("▸ How these scores work"); the page foot is now a calm one-liner. Verified `pass-1/01`. |

### D2 — Exam Readiness
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D2-1 | MAJOR | 3 score cards | Same dead vertical space as D1-1 (cards sized for value+range, abstain text short). | **FIXED** — shared StatCard down-sized abstain value (same `bandValue`/`muted` fix as D1-1). |
| D2-2 | MAJOR | hero + 3 cards | "Not enough data" appears 4× in loud orange on one screen (hero + 3 cards) — repetitive and alarmist for a normal first-run. | **FIXED** — said **once** in the hero; the 3 cards now show a quiet muted "Awaiting reviews" (verified in `pass-1/02`). |
| D2-3 | MINOR | coverage caption | "as of —" renders an em-dash placeholder → looks unfinished. | **FIXED** — clause omitted when no timestamp (`captionText`). |
| D2-4 | MINOR | per-topic table sort | The five 0.12-weight areas are not in a stable/canonical order (arbitrary tiebreak). | **FIXED** — deterministic secondary sort by topic name (`topicRows`). |
| D2-5 | MINOR | 10 identical "no data" rows | Honest but visually flat empty table. | **FIXED (iter 30)** — a single calm hint line ("No reviews yet — per-topic recall appears here after you study. The map below lists every exam area and its weight.") now renders above the table when no topic has recall data yet (`noRecallYet(rows)` + `cfa-readiness__table-hint`); the coverage map still lists all 10 areas + weights. Verified `pass-1/02`. |

**Pass-1 desktop verdict:** the CFA web surfaces are already close to premium
(brand serif lockup, calm palette, real coverage map). The dominant real defects
were (a) abstain-state hierarchy — the empty state shouted in warn-orange and
out-weighted the countdown/CTAs (D1-2, D2-2), and (b) StatCard dead space +
color-semantic collision (D1-1/D2-1, D1-3). **All five Pass-1 desktop MAJORs are
now FIXED, re-captured (`pass-1/`), and re-verified** (`test-e2e` 6/6 green,
`check:eslint`/svelte/tsc green) — the abstain state is now a calm muted-grey
"Awaiting reviews" with the verdict stated once in the hero, and the peach
primary CTA is the single warm accent that leads the eye.

**ALL Pass-1 desktop MINORs FIXED (iter 30)** — D1-4 (CTA-grid asymmetry →
full-width primary + clean 2×2), D1-5 (mixed footer affordances → both pills),
D1-6 (dense methodology paragraph → `<details>` disclosure), D2-5 (flat 10-row
"no data" table → a single calm hint line above the map). Re-captured
(`pass-1/01` + `pass-1/02`) and re-verified: new vitest `readiness.test.ts`
(5 tests green), `test-e2e` 3/3 (cfa_readiness_render), `check:eslint`/svelte/tsc
green. **With this, every CFA-web-page Pass-1 desktop issue (5 MAJOR + 4 MINOR)
is resolved** — the CFA Home + Exam Readiness web surfaces are Pass-1 complete.

### Still-TODO (desktop — deferred to the escalating Pass 2/3)
- Qt-chrome surfaces not yet captured this run: D3 Deadline, D4 Ethics reviewer,
  D6 AI Settings, **D7 Connect/Logout (the objective's named clunky controls)**,
  D8 deck browser, D11 chrome — via `screencapture`/`grab()`. These are the
  native Qt shell (not the CFA web pages fixed above) and are the substance of
  the next desktop pass.
- Populated (real ranges + Bayesian pass/fail call) capture of D1/D2 — needs a
  reviewed collection; the Python payload path is already unit-tested (F4 /
  `bayesian_readiness`), the web render capture is pending.

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
| M1-1 | MAJOR | toolbar + status bar | Stock AnkiDroid light-blue (`#0a9beb`) toolbar/status bar on the primary landing screen — clashes with the navy CFA activities; app doesn't feel like a CFA product on first open. | **FIXED (shell refactor)** — the whole shell derives from `colorPrimary`, so `theme_light.xml` `colorPrimary`→`cfa_navy` + `colorPrimaryDark`→`cfa_navy_hover` re-brands the DeckPicker toolbar AND status bar navy (white title/icons via `actionBarTextColor`). Verified `pass-1-shell/01-deckpicker.png`. |
| M1-2 | MAJOR | deck list | Junk test decks **"h"** and **"h gg"** shipped in the collection — embarrassing leftover data on a premium product. | **FIXED (shell refactor)** — both scratch decks deleted from the device collection (long-press → Delete deck); list is now CFA-only (CFA / Ethics Pairs / Study — Ethics Minimal-Pairs / CFA Exam Priority / CFA Level II). Verified `pass-1-shell/01-deckpicker.png`. |
| M1-3 | MINOR | FAB + no CFA entry | The `+` FAB and sync icon are stock blue; Exam Readiness (the flagship CFA surface) is buried in the drawer with no DeckPicker entry point. | **FIXED (FAB)** — `fab_normal`→`cfa_accent`, `fab_pressed`→`cfa_accent_hover`, so the `+`/Study FAB is now the single warm CFA accent. (Exam-Readiness DeckPicker CTA left as a Pass-2 idea.) Verified `pass-1-shell/01-deckpicker.png`. |

### M2 — Nav drawer
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M2-1 | MAJOR | drawer header | Header is the stock AnkiDroid blue mountain illustration — no CFA logo/wordmark; active item "Decks" highlighted in AnkiDroid blue, not a CFA token. | **FIXED (shell refactor)** — `view_navdrawer_header.xml` replaced with a navy CFA brand lockup (`ankiCFA` wordmark + orange "CFA LEVEL II · EXAM PREP" tagline, no image asset); `drawer_item_text_light.xml` checked-state colour `material_light_blue_500`→`cfa_navy` so the selected item ("Decks") reads CFA-navy. Verified `pass-1-shell/02-nav-drawer.png`. |
| M2-2 | MINOR | icons + labels | "Exam Readiness" uses the same generic bar-chart glyph as "Statistics"; "Support AnkiDroid" reads as upstream, not the product. | Give Exam Readiness a distinct CFA icon; ensure brand consistency of drawer labels. (Pass-2 polish.) |

### M3 — Exam Readiness (flagship CFA screen)
| # | Severity | Element | Issue | Fix direction |
|---|----------|---------|-------|---------------|
| M3-1 | MAJOR | 3 score values | "N/A — abstaining" renders **3× in loud warn-orange** (`CfaExamReadinessActivity.kt:177` → `cfa_warn`) — hierarchy inversion; the *absence* of data is the loudest thing on screen. **Identical to desktop D1-2/D2-2 (already fixed there).** | **FIXED (iter 28)** — abstain is now a calm muted-grey "Awaiting reviews" (`cfa_muted`, non-bold, down-sized 22/18sp) with the give-up reason in the faint sub-line; verified `pass-1/03-exam-readiness.png`. |
| M3-2 | MAJOR | brand eyebrow vs abstain | The orange brand eyebrow "ANKICFA · CFA LEVEL II" is the same warm-orange family as the warn/abstain text → brand accent == warning (colour-semantic collision). **Desktop D1-3 parallel.** | **FIXED (iter 28)** — abstain moved off the warm hue to grey `cfa_muted`, so the orange brand eyebrow is now the single warm accent; `cfa_warn` is reserved for a genuine near-deadline warning (currently unused). |
| M3-3 | MAJOR | 3 score "cards" | Inconsistent card treatment — Readiness sits in a grey filled card (`cfa_surface`) while Memory/Performance are flat/borderless; they aren't consistent cards. | **FIXED (iter 28)** — all three cards now share one container (`drawable/cfa_score_card_bg`: `cfa_surface` fill + `cfa_line` hairline stroke + 12dp radius); the hero is emphasised only by its larger value text. Verified `pass-1/03`. |
| M3-4 | MINOR | status bar | Light-blue status bar sits above the navy toolbar → two-tone band at the very top. | **FIXED (shell refactor)** — `android:statusBarColor` = `?attr/colorPrimary` = `cfa_navy` app-wide now, so CFA activities have a single navy band top-to-toolbar. Verified `pass-1-shell/03-exam-readiness.png`. |
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
| M5-1 | MAJOR | whole chrome | Reviewer is 100% stock AnkiDroid: light-blue toolbar, light-blue "99 1 0" count bar, default ease-button colours — zero CFA identity on the screen users spend the most time on. | **FIXED (shell refactor)** — Reviewer toolbar is now navy (shared `colorPrimary`); the count-bar `topBarColor` `material_light_blue_100`→`cfa_surface` (calm CFA grey). Verified `pass-1-shell/05-reviewer-question.png` / `06-reviewer-answer.png`. |
| M5-2 | MINOR | ease buttons | Stock red/grey/green/blue ease bar; count-bar background light-blue. | **INTENTIONALLY KEPT** — the four-grade ease palette (Again red / Hard grey / Good green / Easy blue) is a learned Anki affordance; recolouring it risks confusing the grade semantics, so it is preserved. Count-bar bg now `cfa_surface` (fixed with M5-1). |

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

**Shell refactor — the remaining Pass-1 mobile MAJORs — NOW FIXED (this iter):**
M1-1 (DeckPicker toolbar/status bar), M2-1 (nav-drawer header + selected item),
M5-1 (Reviewer chrome), plus M1-2 (junk scratch decks purged) and the MINORs
M1-3 (accent FAB) / M3-4 (status-bar band). This was the objective's flagged
"non-native-CFA feel / full AnkiDroid CFA UI refactor is the biggest lift": the
whole shell derives from `colorPrimary`, so re-branding it `cfa_navy` in
`theme_light.xml` (the shipped default day theme) re-themes the DeckPicker, nav
drawer, Reviewer, status bar, tab bar and action mode in one place; the FAB/Study
button becomes the single warm `cfa_accent`; the nav-drawer header is a navy CFA
lockup; and the selected drawer item is CFA-navy. Device-observable after set:
`AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-1-shell/` (before =
`pass-1-before/`). Green after the change: `lintVitalFullRelease`, `ktlintCheck`,
CFA unit tests. **With this, ALL Pass-1 mobile MAJORs (7/7) are resolved** — the
app now reads as a cohesive navy CFA product end-to-end, not "AnkiDroid with two
bolt-on CFA screens." Remaining mobile items are MINORs (M2-2 drawer icon, M4-2
config density) + the escalating Pass-2/Pass-3 critiques.

## Pass 2 — DESKTOP (harsher): Qt-chrome native surfaces

Pass 1 covered the CFA *web* pages (Home, Readiness). Pass 2 turns the harsher
lens on the **native Qt chrome** — the top toolbar and its account controls —
starting with the objective's **named must-fix: "the clunky Connect and Logout
controls."**

Captures (faithful standalone render of the real top-bar markup + the real
`cfa_chrome._toolbar_css()` + base `toolbar.css`, screenshotted with
`chrome-devtools-axi`; the Qt webview renders this exact HTML/CSS):
- `desktop-ui/pass-2-before/connect-logout.png` (+ `.html`) — the old bar.
- `desktop-ui/pass-2/connect-logout.png` (+ `.html`) — the redesigned bar,
  logged-out **and** logged-in states.

### D7 — Connect / Log out controls (the named clunky controls)
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D7-1 | MAJOR | top-bar sync cluster | **Three** always-visible sync links sat in a row — `Sync` **+** `Connect` **+** `Log out` — regardless of state. `Connect` showed even when already connected; `Log out` showed even when logged out. Two of the three were dead/no-op in any given state — clunky and confusing (which one applies now?). | **FIXED (iter 31)** — replaced the always-visible Connect+Log out pair with **one context-aware account control** (`Toolbar._create_account_link` → pure `cfa_sync_connect.account_link_spec`): logged-out → `Connect`, logged-in → `Log out` (tooltip names the account). Keys off `pm.sync_auth()`; `connect_cfa_sync`/`logout_of_sync` now `toolbar.draw()` so the control flips immediately. Before/after in `pass-2/`. |
| D7-2 | MINOR | affordance | The sync-account link was visually identical to the Home/Study/Ethics/Readiness *navigation* links — no signal it manages an account, not a page. | **FIXED (iter 31)** — the single account control renders as a distinct **bordered chip** (`#cfa_account` in `cfa_chrome._toolbar_css`), set apart from the plain nav links, warm-accent border/hover; discoverable without crowding the bar. |

**Verification:** `qt/tests/test_cfa_toolbar.py` extended with 6 tests (spec
logged-out=Connect / logged-in=Log out naming the account / safe without a name;
`_create_account_link` flips handler+label with login state; `_centerLinks`
builds exactly one `_create_account_link()` and the old `"cfa_connect"` /
`"cfa_logout"` create_link pair is gone). `test_cfa_toolbar` + `test_cfa_menu` +
`test_cfa_chrome` **25/25 green**; ruff check + format clean. The CFA *menu*
keeps both explicit entries (a menu enumerates all actions; each self-guards).

### D9 — Populated render of Home + Readiness (the returning-learner state)
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D9-1 | MAJOR | Readiness / Home whole page | Only the honest zero-review ABSTAIN state had ever been captured. The named must-fix asks for the pages to "render the three scores, RANGES, and coverage map with REAL data" — the *populated* returning-learner state (real ranges + a lit coverage map + a Bayesian pass/fail call) was never proven, so half the must-fix was unevidenced. | **FIXED (iter 32)** — added `tools/cfa/seed_reviews.py` (seeds a graded review history that crosses every give-up threshold on the real shared engine) + a `CFA_SEED_REVIEWS` hook in `launch_anki_for_e2e.py` + `ts/tests/e2e/cfa_readiness_populated.test.ts` (2 green). Captured `pass-2/01-cfa-home-populated.png` + `02-cfa-readiness-populated.png`: Memory 77%–81%, Performance 59%–79%, Readiness 42%–92%, hero "likely pass p=0.59", coverage 100% (10/10), 320 graded reviews. Evidence `pass-2/populated-render.txt`. |
| D9-2 | MINOR | per-topic recall column | First seed attempt rendered a degenerate flat "100%–100%" recall for every topic — reads as fake seed data on a premium product. | **FIXED (iter 32)** — the seeder now gives each card a distinct elapsed/stability ratio so the FSRS forgetting curve yields a realistic per-topic recall SPREAD (69%–92% across the 10 areas), unit-tested (`test_recall_spread_is_realistic_not_flat`). |

**Populated-render verdict:** with the returning-learner capture, BOTH halves of
the named "Readiness renders with real data" must-fix are now evidenced — the
honest first-run abstain (Pass 1) AND the real-range / Bayesian-call populated
state (this pass). The premium Pass-1 fixes (calm hero, symmetric CTA grid,
`<details>` methodology disclosure) all hold in the populated state too. All
score ranges stay honestly labelled ("not validated against real exam data",
wide uncalibrated band) and are computed with **no AI**.

### Still-TODO (desktop Pass 2/3)
- Remaining Qt-chrome surfaces: D3 Deadline dialog, D4 Ethics reviewer, D6 AI
  Settings dialog, D8 deck browser, D11 window chrome — capture + critique.

## Pass 2 (harsher) — MOBILE: TODO
## Pass 3 (ruthless, pixel-level) — TODO (both apps)
