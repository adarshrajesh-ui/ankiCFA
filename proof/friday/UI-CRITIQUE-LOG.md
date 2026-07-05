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

### D3 — Deadline planner ("Peak on exam day")
Captures (real backend, `ts/tests/e2e/cfa_deadline_render.test.ts`, both states):
- `desktop-ui/pass-2-before/03-cfa-deadline-ranked.png` + `04-cfa-deadline-empty.png`
- `desktop-ui/pass-2/03-cfa-deadline-ranked.png` + `04-cfa-deadline-empty.png`

This shipped desktop surface (`/cfa-deadline/{deckId}` → `CfaDeadlinePage.svelte`)
had **never been captured or critiqued** in any Phase-B pass — a real inventory
gap (D3 in `UI-INVENTORY.md`). Captured this pass and critiqued:

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D3-1 | MAJOR | ranked table (recall + interval columns) | On a fresh / all-new deck the "weakest-first ranking" rendered **50 identical rows of warn-orange `0.0%` + `0`** — a wall of alarming orange that (a) is a hierarchy-inversion / colour-semantic shout (the *absence* of a memory model is the loudest thing on screen — the same defect fixed on Home/Readiness D1-2/D2-2/D1-3), and (b) is **misleading**: a never-studied card has no FSRS memory state, so `0.0%` is a placeholder-by-construction (`deadline_retention_with_new` assigns new cards recall 0.0), **not** a real "you will forget everything" figure. | **FIXED (iter 33)** — the payload (`mediasrv._cfa_deadline_payload`) now flags never-studied cards (`isNew`, via the deck's `is:new` set) and never warn-colours a row that only reads 0.0 because it has no data yet. `CfaDeadlinePage` renders a new card's recall as a **calm muted "New"** (not warn-orange `0.0%`) and its interval as a muted en-dash, with a one-line hint above the table ("Every card here is new — a predicted exam-day recall appears for each once you've studied it…"). Genuinely at-risk **studied** cards keep the warn-orange `recall < 0.85` semantic. Verified `pass-2/03`: zero `.is-warn` rows on the fresh deck, calm "New" column + hint. |
| D3-2 | MINOR | empty state (non-CFA deck) | The "No due cards to rank yet." warn Notice + helper caption is honest and calm — no defect. Kept as-is; documented for completeness (`pass-2/04`). | No change needed. |

**Verification:** `ts/lib/cfa/pages/deadline.ts` pure helpers (`recallCell`,
`intervalCell`, `newCardCount`, `allNew`, `newCardHint`) + `deadline.test.ts`
(7 vitest tests, green — asserts a new card renders "New" never "0.0%", the
all-new hint, mixed-deck count/plural, studied-only → no hint).
`ts/tests/e2e/cfa_deadline_render.test.ts` (2 e2e, green vs the REAL backend)
captures both states and asserts the fresh-deck table has **zero** warn-orange
rows + the calm "New" cells + the hint. Full `check:vitest` 62/62,
`check:eslint`/svelte/typescript green; `ruff check`/`format` clean on
`mediasrv.py`.

### D4 — Ethics minimal-pairs reviewer (the flagship CFA card)
Captures (real template + `style.css`, a genuine end-to-end attempt driven by the
REAL shared front-template JS grader, screenshot via `chrome-devtools-axi`):
- `desktop-ui/pass-2-before/d4-ethics-{blank,partial,perfect}.png` + `…-perfect-zoom.png`
- `desktop-ui/pass-2/d4-ethics-{blank,partial,perfect}.png` + `…-perfect-zoom.png`
- Evidence: `desktop-ui/pass-2/d4-ethics-reviewer.txt`

This surface — `cfa/ethics_pairs/templates/front.html` — had **never been
captured or critiqued** in any Phase-B pass (a real inventory gap, D4). It is the
product's flagship learning card. Captured all three states and critiqued:

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D4-1 | MAJOR | gold answer-key phrase (graded reveal) | The true decisive phrase is highlighted with the brand-green "gold" outline, but each word is a separate `.cfa-tok` span and the old CSS drew a **full four-sided `box-shadow` inset on EVERY token** (`.cfa-tok.gold { box-shadow: 0 0 0 2px var(--cfa-brand-green) inset }`). So a multi-word decisive phrase — "exact unreleased quarterly earnings figure" (5 words) + "sells the company out of her clients' portfolios." (8 words) — rendered as a **ladder of 13 disconnected green boxes** with an interior vertical divider between every word (see `pass-2-before/d4-ethics-perfect-zoom.png`). It fragments the visual meaning of "phrase," reads as a rendering bug, and is clearly sub-premium on the flagship card — the same "presentation fights the meaning" family as D1-2/D2-2. | **FIXED (iter 35)** — composed the outline from four inset **edge** rules and **open the interior edges between contiguous gold tokens** so a run reads as ONE outlined span, while a lone gold token stays a full rounded pill: `.cfa-tok.gold` (all four edges) → `.cfa-tok.gold + .cfa-tok.gold` (prev gold: open left) → `.cfa-tok.gold:has(+ .cfa-tok.gold)` (next gold: open right) → `.cfa-tok.gold + .cfa-tok.gold:has(+ .cfa-tok.gold)` (interior: top+bottom only), night-mode mirrored. Both phrases now render as continuous outlined spans with caps only at the true run start/end (`pass-2/d4-ethics-perfect-zoom.png`); generalizes across the pick tiers (verified in `pass-2/d4-ethics-partial.png`) and carries to the one-passage card (shared CSS). |
| D4-2 | — | pre-attempt / partial / standard reveal | The fresh state (cluster over-line, serif question, two co-presented vignettes, verdict buttons, highlight step + CTA), the partial-credit grade band ("Partial credit — you matched some evidence…"), the per-span ✓/✗ breakdown, the GOVERNING STANDARD reveal + rationale all render cleanly and honestly. No defect. | No change needed (documented for completeness). |

**Verification:** `cfa/ethics_pairs/tests/test_gold_outline_css.py` (5 stdlib
tests) locks the continuous-run selectors and asserts the old per-token full box
is gone. Full ethics suite `pytest cfa/ethics_pairs/tests -q` → **121 passed,
3 skipped** — the byte-mirrored shared JS grader (`test_highlight.py`,
Python↔JS grade agreement) is untouched (the fix is `style.css`-only, not the
`CFA-SPAN-SHARED` JS block).

### D6 — AI Settings dialog (`qt/aqt/cfa_ai_settings.py`)
Captures (real `CfaAiSettingsDialog`, offscreen `QDialog.grab()` → PNG, no live
Anki launch; reproduce with `just cfa-capture-ai-settings`):
- `desktop-ui/pass-2-before/d6-ai-settings-{master-on,master-off}.png`
- `desktop-ui/pass-2/d6-ai-settings-{master-on,master-off,key-present}.png`
- Evidence: `desktop-ui/pass-2/d6-ai-settings.txt`

This native Qt dialog (the visible desktop AI on/off control) had **never been
captured or critiqued** in any Phase-B pass. It was a bare vertical stack of
three checkboxes + one dense grey paragraph + Save/Cancel — the generic-add-on
look, no CFA identity, and (worse) it never told the user whether AI would
actually run. Captured and critiqued:

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D6-1 | MAJOR | whole dialog | No brand identity — a bare checkbox stack with no eyebrow/title, unlike every other CFA surface (Home, Readiness, mobile all carry the brand lockup). Reads as a stock Anki add-on sheet, not a premium CFA product. | **FIXED (iter 37)** — added the CFA brand heading (eyebrow "ankiCFA · AI" + serif title "AI features") via `cfa_style.page_heading`. |
| D6-2 | MAJOR | 3 checkboxes | The master switch (which gates the two feature switches) was a flat peer in the list; the parent/child relationship was invisible — on master-off the two just greyed out with no grouping. | **FIXED (iter 37)** — the master switch stands alone with a subtitle; the two per-feature switches are in ONE indented container under a quiet "PER FEATURE" divider that greys out **as a group** when the master is off (`self._features.setEnabled(on)`). |
| D6-3 | MAJOR | key gating | The whole contract hinges on "AND an OpenAI API key is configured", but the dialog never said whether one IS — the user couldn't tell if the switches would reach the model or silently fall back. Buried in a 4-line prose block. | **FIXED (iter 37)** — a live status line states it up front: key present → green (pass) "OpenAI API key detected — AI runs for the switches you enable"; no key → orange (warn) "No OpenAI API key set — every feature runs its offline fallback." Reads `cfa.ai.llm_client.key_present()` (the exact gate the AI modules use); the key value is never shown/logged. |
| D6-4 | MINOR | spacing / note | Cramped checkbox rows; dense grey paragraph butting the buttons. | **FIXED (iter 37)** — consistent spacing scale + a hairline divider before a single quiet caption footnote. |

**Verification:** `qt/tests/test_cfa_ai_settings.py` → **8 passed** (5 prior + 3
new: feature-group container gating, `_status_html` reflects key presence + never
leaks a key, brand heading present). Broader CFA qt suite (ai_settings + toolbar +
menu + chrome + home) → **39 passed**; `ruff check`/`format` clean. Parity-gated
`cfa_style` TOKENS values UNCHANGED — the redesign only composes existing builders
(`page_heading`/`section`/`caption`/`notice`) and reassigns state→tone.

### D8 — Deck browser (CFA-skinned deck list)
Captures (the EXACT webview surface — compiled base `deckbrowser.css` + live
`cfa_chrome._deckbrowser_css()` + banner over a realistic CFA deck tree,
screenshot via `chrome-devtools-axi`; reproduce with `just cfa-capture-deck-browser`):
- `desktop-ui/pass-2-before/d8-deck-browser.png` (+ `.html`)
- `desktop-ui/pass-2/d8-deck-browser.png` (+ `.html`)
- Evidence: `desktop-ui/pass-2/d8-deck-browser.txt`

The main-window deck list (`DeckBrowser` webview re-skinned by `cfa_chrome.py`)
was listed as a Still-TODO Pass-2 surface — **never captured or critiqued** in
any prior pass. Captured this pass and critiqued:

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D8-1 | MAJOR | filtered deck names + "New" counts | Although the shell + toolbar were branded navy, the deck LIST itself still leaked stock Anki blue in two places (the desktop parallel of the mobile **M6-1** defect): the filtered/dynamic deck NAMES ("Ethics Pairs", "Study — Ethics Minimal-Pairs", "CFA Exam Priority") rendered in stock blue `--fg-link` #1d4ed8 (the base `.filtered { color: var(--fg-link) !important }` beat the CFA `a { color: ink }` on both specificity AND `!important`), and the "New" COUNT numbers (20/29/99/1) rendered in stock blue `--state-new` #3b82f6 (`.new-count { color: var(--state-new) }`). The deck list — the first screen after Home — read blue-accented despite the navy shell: the exact "non-native-CFA feel" the objective flags. | **FIXED (iter 38)** — `cfa_chrome._deckbrowser_css()` now retones both to brand navy: `a.deck { color: ink !important }`, `a.deck.filtered { color: ink !important }` (matches Anki's specificity + the `.filtered !important` so it wins the cascade), and `.new-count { color: ink !important }`. Curated CFA study decks read in brand navy → one cohesive branded list. The "New" count keeps the three-way distinction (new = navy, learn = red, review = green); the learned Anki learn/review count semantics are **unchanged** (M5-2/M6-1 decision), orange top-bar accent stays the single warm accent. Presentation-only (no token value change). Verified `pass-2/d8-deck-browser.png`. |
| D8-2 | — | brand banner + footnote + page tint | The "ankiCFA · Level II / Your decks" banner, the CFA page tint (`primary_soft`), the calm hairline table rules, and the CFA footnote all render cleanly. No defect. | No change needed (documented for completeness). |

**Verification:** `qt/tests/test_cfa_chrome.py` → **7 passed** (5 prior + 2 new:
`test_deckbrowser_retones_stock_blue_leaks` locks the three navy-`!important`
retone rules; `test_deckbrowser_keeps_learn_review_count_semantics` asserts the
learn/review count colours are NOT recoloured). Broader CFA qt suite (chrome +
toolbar + menu) → **27 passed**; `ruff check`/`format` clean; parity-gated
`cfa_style` TOKENS values UNCHANGED (the fix only reassigns which token the
deck-list states use). `just cfa-chrome-test` / `just cfa-capture-deck-browser`.

### D11 — Window chrome: the top-level CFA menu (menu bar)
Captures (real `aqt.cfa.setup_menu` built against a QMenuBar stand-in — exactly
as `qt/tests/test_cfa_menu.py` — popped up offscreen and grabbed to PNG;
reproduce with `just cfa-capture-cfa-menu`):
- `desktop-ui/pass-2-before/d11-cfa-menu.png` — the old flat list.
- `desktop-ui/pass-2/d11-cfa-menu.png` — the grouped, sectioned menu.
- Evidence: `desktop-ui/pass-2/d11-cfa-menu.txt`

The desktop window chrome (the CFA menu on the menu bar) was the last
Still-TODO Pass-2 surface — never captured or critiqued in any prior pass.
Captured this pass and critiqued:

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D11-1 | MAJOR | whole CFA menu | The eight actions were a **flat, undifferentiated list** — a dashboard (CFA Home), a report (Exam Readiness), three study modes, a settings dialog, and two account controls all as sibling rows at the same level, with no grouping. A user scanning the menu can't tell "go somewhere" from "study" from "settings/account"; it reads as a stock add-on dump, not a premium product's information architecture. | **FIXED (iter 39)** — grouped into three **labelled native sections** via `addSection`: **Dashboard** (CFA Home, Exam Readiness…), **Study modes** (Study Ethics Minimal-Pairs, Study by Exam Priority, Peak-on-Exam-Day (Deadline)…), **Settings & account** (AI Settings…, Connect to CFA Sync server, Log out of Sync…). Section headers degrade gracefully to plain separators on platforms that don't render section text. Verified `pass-2/d11-cfa-menu.png`. |
| D11-2 | MINOR | every action | No hover discoverability — a menu row gives no hint of what it does before you click it. | **FIXED (iter 39)** — each command now carries a concise `setStatusTip` (e.g. "See your memory, performance and readiness scores with honest ranges."), shown in the main-window status bar on hover — a standard premium desktop affordance. |
| D11-3 | — | account entries (Connect / Log out) | Both are always present regardless of login state (unlike the toolbar D7 chip, which is context-aware). | **Kept as-is (documented decision).** A *menu* enumerates all available actions and each handler self-guards (Log out no-ops + informs when already logged out; Connect is idempotent). The always-visible top-bar chip (D7) is the context-aware surface; the menu is the exhaustive one. |

**Verification:** `qt/tests/test_cfa_menu.py` → **13 passed** (11 prior +
2 new: `test_cfa_menu_is_grouped_into_labelled_sections` asserts the three
section headers in order + a status-tip on every command;
`test_cfa_menu_sections_order_commands_correctly` asserts each command falls
under the right section and none leaks ahead of the first header). The prior
count/label tests now filter separators via a `_command_actions` helper (still
exactly the 8 commands, unchanged order). CFA menu + toolbar + chrome →
**29 passed**; `ruff check`/`format` clean; no `cfa_style` token touched
(structure-only change to `setup_menu`).

### Still-TODO (desktop Pass 2/3)
- Pass 2 desktop is **complete** — every inventoried Qt-chrome + web surface
  (D1–D11) captured, critiqued, and all MAJORs fixed. Remaining desktop work is
  the escalating **Pass 3 (ruthless, pixel-level)** sweep.

## Pass 2 — MOBILE (harsher): stock-blue leaks through the navy shell

Pass 1 branded the shell navy (toolbar, status bar, nav drawer, Reviewer, FAB)
and resolved all 7 Pass-1 MAJORs. The harsher Pass-2 lens re-captured the primary
screens on `emulator-5554` (real running debug build) and looked specifically for
*residual* stock-AnkiDroid colour leaking through the new navy shell.

Captures (before = current post-shell-refactor state; after = this pass), branch
`gnhf/speedrun-mobile` at `AnkiDroid: proof/gnhf-speedrun/mobile-ui/`:
- `pass-2-before/01-deckpicker.png`, `03-exam-readiness-top.png`,
  `04-exam-readiness-bottom.png`
- `pass-2/01-deckpicker.png`, `02-nav-drawer.png`, `deckpicker-brand.txt`

### M6 — DeckPicker (residual stock-blue on the primary landing screen)
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| M6-1 | MAJOR | filtered deck names + "new" counts | After the shell went navy, TWO stock-AnkiDroid blue tokens still leaked on the first screen the user opens every session: the **filtered/dynamic deck NAMES** ("Study — Ethics Minimal-Pairs", "CFA Exam Priority") rendered in stock blue (`dynDeckColor` = `#2222bb`), and the **"new" card COUNT numbers** (20 / 29 / 99 / 1) rendered in indigo-blue (`newCountColor` = `@color/material_indigo_700`). Together the DeckPicker read blue-accented despite the navy shell — the exact "non-native-CFA feel" the objective flags. | **FIXED (iter 34)** — in `theme_light.xml` (shipped default day theme) both tokens now point at `@color/cfa_navy`. The CFA study decks are curated study modes, not an Anki implementation detail to surface in loud blue, so their names read in brand navy → one cohesive branded deck list. The "new" count keeps the three-way distinction (new = navy, learn = red, review = green); the semantic learn/review colours (the learned Anki affordance) are unchanged, matching the M5-2 decision. Orange FAB stays the single warm accent. Before `pass-2-before/01` → after `pass-2/01` + `02`. |

**Verification:** `./gradlew :AnkiDroid:installFullDebug` (BUILD SUCCESSFUL) →
device-observable after capture; `:AnkiDroid:lintVitalFullRelease` + `ktlintCheck`
**BUILD SUCCESSFUL**. Theme-resource-only change (no Kotlin) so the `*Cfa*` unit
tests are unaffected. `material_indigo_700` is a library (`anki-common`) colour
with other definitions, so dropping the app reference does not trip
`UnusedResources`.

### M7 — Exam Readiness (flagship CFA screen, harsher re-look)
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| M7-1 | MAJOR | the three abstain score cards | In the awaiting-data state all three honest cards render the shared engine's give-up `reason` verbatim, and the engine's READINESS reason is a literal concatenation of the memory + performance reasons — so the hero card repeated the SAME counts ("22 graded reviews (need 200), 0% topic coverage (need 50%)" / "21 first-seen questions (need 30)") that already appear on the two cards below AND in the evidence caption. The user reads the same numbers **three times** on one screen: verbose, low-signal, not premium. Same defect the desktop team fixed in iter 26 ("state the verdict once in the hero, reason in the faint sub-line"). | **FIXED (iter 40)** — `CfaExamReadinessActivity.render()`: when BOTH inputs still abstain, the hero READINESS card shows a **concise composite sub-line** (new string `cfa_readiness_abstain_hint` = "Keep studying — the Memory and Performance scores below need more data first.") via a new `abstainOverride` param on `scoreCard()`, instead of the verbatim engine reason. When only one input abstains (partial), the full engine reason is still shown (no information hidden). The specific counts stay HONEST + visible on the MEMORY card, the PERFORMANCE card, and the evidence caption. Presentation-only — the shared `computeCfaScores` RPC, the abstain give-up rule, and every count are untouched. Before `pass-2-before/03-readiness-repeat.png` → after `pass-2/03-readiness-deduped.png` (+ `pass-2/readiness-dedup.txt`). |

**Verification:** `installFullDebug` (device-observable after capture on `emulator-5554`),
`ktlintCheck`, `lintVitalFullRelease` (release-only; new string referenced → no
`UnusedResources`), and `testPlayDebugUnitTest --tests "com.ichi2.anki.cfa.*"` — all
**BUILD SUCCESSFUL**. Committed on `gnhf/speedrun-mobile`.

### M4 — Exam Config (harsher re-look: sparse screen / no rationale)
Captures (branch `gnhf/speedrun-mobile`, `emulator-5554`, real fullDebug build):
- `pass-2-before/05-exam-config-sparse.png` — genuine pre-fix screen on the
  CURRENT navy shell (git-stash the M4-2 source → `installFullDebug` → capture →
  stash pop, so before/after differ ONLY by this fix, not the shell refactor).
- `pass-2/05-exam-config-context.png` (context line, no-date) +
  `pass-2/06-exam-config-countdown.png` (live countdown with a date set).
- Evidence: `pass-2/exam-config-density.txt`.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| M4-2 | MINOR (carried from Pass 1) | whole screen | The Exam-config screen was a bare title + "No exam date set" field + Pick date + Save over a ~60% empty lower half, with **no explanation of why the exam date matters** and **no feedback once a date was chosen** — reads as unfinished on a premium exam-prep product. | **FIXED (iter 41)** — added (a) a calm `cfa_muted` **context line** under the title ("Set your exam date so ankiCFA can weight study by points-at-stake and show a live countdown on the Exam Readiness screen.") and (b) a **live countdown preview** in the warm `cfa_accent` shown the moment a date is set / on re-open ("N days to the exam" via a `plurals`, "Your exam is today — good luck." on the day, "This exam date has already passed." after), hidden when no date is set. Backed by a pure, unit-tested `CfaExamConfig.daysUntil(date, today)` (whole days, positive/0/negative, null on unset/blank/unparseable). Presentation-only — the persisted `cfa_exam_config` col.conf shape (the synced key that drives both apps) is untouched. |

**Verification:** `testPlayDebugUnitTest --tests "com.ichi2.anki.cfa.CfaExamConfigTest"`
→ **7 tests green** (3 prior persistence + 4 new `daysUntil`); `ktlintCheck` +
`lintVitalFullRelease` (plurals carry both one/other forms, all new strings
referenced → no `UnusedResources`) + `installFullDebug` all **BUILD SUCCESSFUL**.
Committed on `gnhf/speedrun-mobile`.

### M8 — Reviewer (harsher sweep of the highest-time-on-screen surface)
Captures (branch `gnhf/speedrun-mobile`, `emulator-5554`, real fullDebug build):
- `pass-2-before/07-reviewer-showanswer-bluegrey.png` — the CURRENT navy shell
  WITHOUT this fix (the installed build predated it): the "Show answer" CTA is a
  stock blue-grey bar.
- `pass-2/07-reviewer-showanswer-navy.png` (Show-answer CTA now brand navy) +
  `pass-2/08-reviewer-ease-buttons-intact.png` (answer side — the four-grade ease
  colours preserved).
- Evidence: `pass-2/reviewer-showanswer.txt`.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| M8-1 | MAJOR | "Show answer" primary CTA | Pass 1 branded the Reviewer's toolbar navy and its count bar `cfa_surface`, but the single **primary call-to-action on the screen users spend the most time on** was still stock AnkiDroid: the legacy reviewer's flip button (`R.id.flashcard_layout_flip`) reused `@style/HardButton` + `?attr/hardButtonRef`, both resolving to the stock blue-grey Hard ease colour (`hardButtonBackground` / `footer_button_hard` = `@color/material_blue_grey_700`); with card animation on it's redrawn via `footer_button_ripple`, which reads `?attr/answerButtonBackground` off the view's theme overlay → blue-grey there too. So the "Show answer" button read as a muted stock blue-grey with zero CFA identity (and looked identical to the unrelated Hard ease button). The new reviewer (`view_answer_area.xml`) had the parallel leak: `?showAnswerButtonBackground` = `@color/material_blue_700` (stock blue). | **FIXED (iter 42)** — new `drawable/footer_button_showanswer` (default `cfa_navy`, pressed/focused `cfa_navy_hover`) + new `@style/CfaShowAnswerButton` (`answerButtonBackground=cfa_navy`, so the animation/ripple path renders navy too, not just the static bg); `flashcard_layout_flip` now uses that drawable + theme instead of `hardButtonRef`/`HardButton`; `theme_light.xml showAnswerButtonBackground` `material_blue_700`→`cfa_navy` (new-reviewer parity). The "Show answer" CTA is now brand navy, matching the toolbar → one cohesive navy product. Presentation-only — the Hard ease button (`ease2`) still uses `?attr/hardButtonRef` + `@style/HardButton`, so the learned four-grade ease scheme (again=red / hard=blue-grey / good=green / easy=light-blue) is **unchanged** (verified `pass-2/08`). Before `pass-2-before/07` → after `pass-2/07` (+ `08`). |

**Verification:** `installFullDebug` (device-observable after capture on
`emulator-5554`), `ktlintCheck`, `lintVitalFullRelease` (new drawable/style/string
all referenced → no `UnusedResources`), and `testPlayDebugUnitTest --tests
"com.ichi2.anki.cfa.*"` — all **BUILD SUCCESSFUL**. Committed on
`gnhf/speedrun-mobile`. **With M8, every inventoried mobile surface (DeckPicker,
nav drawer, Exam Readiness, Exam Config, Reviewer) is captured+critiqued and all
Pass-2 MAJORs fixed → Phase B Pass 2 mobile COMPLETE.**

### Still-TODO (mobile Pass 3)
- Carried MINORs: M2-2 generic drawer icon for Exam Readiness —
  *resolved: `ic_cfa_readiness` bar-chart icon is wired in `navigation_drawer.xml`*;
  M4-2 sparse Exam-Config density — *resolved (iter 41)*; M3-5 per-topic
  8→10 topic parity when the AAR is rebuilt from the 10-topic branch.

## Pass 3 — DESKTOP (ruthless, pixel-level): accessibility / contrast

Pass 1 fixed the loud hierarchy/colour defects; Pass 2 captured & fixed every
remaining surface (D1–D11). The ruthless Pass-3 lens goes below the eye to the
*measured* rendering quality a premium product owes every user — starting with a
**scientific WCAG 2.1 AA contrast audit** of the shared design tokens (not a
by-eye critique: contrast ratios are computed from the actual hex values).

Captures (before = decorative `$cfa-faint` #939597 colouring text; after = the
new AA-safe `$cfa-faint-ink` #68707d), same populated seed, differ ONLY by this
fix (stash→rebuild→capture before→pop→rebuild):
- `desktop-ui/pass-3-before/01-cfa-home-populated.png`, `02-cfa-readiness-populated.png`
- `desktop-ui/pass-3/01-cfa-home-populated.png`, `02-cfa-readiness-populated.png`,
  `03-contrast-audit-proof.png` (side-by-side swatch + computed ratio table),
  `contrast-audit.txt`

### D-P3-1 — Tertiary text fails WCAG AA (the audit finding)
| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P3-1 | MAJOR (accessibility) | every faint caption / meaning / sub-line | The design token `$cfa-faint` (#939597), documented "captions / disabled", was colouring **readable text** across the product (StatCard sub-lines + the "Awaiting reviews" abstain value, the score-meaning lines on Home & Readiness, `Caption tone="faint"`, the Hero sub, the per-topic "no data" recall cell). Measured contrast: **3.01:1 on white** (< the 4.5:1 AA-body bar) and **2.90 / 2.77 on the page / surface tints — below even the 3:1 large-text floor**. On a premium exam-prep product, the honest secondary information (what each score means, the midpoint, the give-up reason) was the hardest thing on the page to read. | **FIXED (iter 43)** — parity-safe (iter-26 pattern: reassign *which* token a usage points at, never change a parity-gated value). `$cfa-faint` (#939597) is now **decorative-only** (scrollbar thumb, Notice rule, desktop disabled-button bg) with its parity-gated value untouched (cfa_style.py stays byte-identical — desktop uses faint as a bg, never text). A new web-only **`$cfa-faint-ink` (#68707d)** navy-tinted AA-safe tertiary-**text** token clears AA body on **all three** backgrounds (5.00 / 4.83 / 4.60) while staying lighter than `$cfa-muted` (6.85) so the `ink > muted > faint-ink` type hierarchy is preserved. Repointed 8 text usages. |

**Verification:** `ts/lib/cfa/contrast.test.ts` (**16 vitest tests, green**) — a
self-contained audit that parses the hexes out of `_tokens.scss`, asserts every
text token clears AA on every background, the faint-ink fix, the hierarchy, the
semantic triad + mm-green role, DOCUMENTS why faint fails AA, and a **regression
guard** that scans the 8 components and fails if `color: cfa.$cfa-faint` (text)
ever returns. Full CFA vitest **28/28**; `./ninja check:svelte check:typescript
check:eslint` all green; the two populated e2e specs still 2/2. **Honesty:** the
GPT-4o vision critic is still unavailable (no `OPENAI_API_KEY`); the ratios are
*computed*, which is stronger than a vision opinion for this class of defect.

### D-P3-2 — Interactive control boundaries fail WCAG 1.4.11 (non-text contrast)

The text audit (D-P3-1) checked text-on-background; the ruthless lens then went
to the *other* half of accessible contrast — the boundary that makes an
interactive control **perceivable**.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P3-2 | MAJOR (accessibility) | secondary Study CTAs (`.cfa-home__cta`), footer chips (`.cfa-home__chip`), Deadline date input (`.cfa-deadline__date-input`) | These controls have a **white fill on the near-white page** and draw their only boundary with the DECORATIVE hairline `$cfa-line` (#e7e9ec) — measured **1.22:1 on white / 1.17:1 on page / 1.12:1 on surface**, far below the **3:1** WCAG 2.1 SC **1.4.11** requires for the boundary of an active UI component. The four secondary Study tiles and the two footer chips therefore **float invisibly** (white-on-near-white); a low-vision user can't tell they're tappable. (The primary CTA is exempt — accent-soft fill + accent border. Card edges / table rules / dividers are pure decoration, which 1.4.11 exempts, so they keep the hairline.) | **FIXED (iter 45)** — parity-safe (add a token, never change the parity-gated `$cfa-line` value). New web-only **`$cfa-control-border` (#7e8896)**, a navy-tinted mid grey that clears **3:1 as a control edge on all three backgrounds (3.59 / 3.47 / 3.31)** while staying far lighter than `$cfa-muted` (6.85) so it reads as an edge, never text. Repointed the 3 interactive-control borders; every decorative hairline stays `$cfa-line`. |

**Verification:** `ts/lib/cfa/contrast.test.ts` extended **16 → 21 vitest tests
(green)** — a new "control-boundary contrast audit (WCAG 2.1 SC 1.4.11)" block:
DOCUMENTS why `$cfa-line` fails as a control edge (<3:1), asserts the new
`$cfa-control-border` clears 3:1 on white+page, asserts it stays lighter than
`$cfa-muted` (an edge, never text), a FIX check (Home CTA+chip ≥2 uses + Deadline
input) and a **regression guard** that the decorative components (Band /
DataTable / Hero / StatCard) keep the exempt hairline. Full CFA vitest **33/33**;
`./ninja check:svelte check:typescript check:eslint` all green. Device-observable
before/after (same populated seed, stash-isolated) + a FAIL→PASS ratio swatch
under `desktop-ui/pass-3-nontext{,-before}/` + `nontext-contrast.txt`. **Honesty:**
ratios are *computed* (sRGB relative luminance), no vision model, no AI in render.

### D-P3-3 — At-risk status flagged by colour alone (WCAG 1.4.1 Use of Color)

D-P3-1/D-P3-2 audited contrast *ratios*; the ruthless lens then went to the
*channel* question — is any information carried by colour **alone**? WCAG 2.1 SC
**1.4.1** (LEVEL A — the most fundamental bar, deeper than the AA findings above)
forbids it.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P3-3 | MAJOR (accessibility) | Deadline planner at-risk recall cell (`.cfa-deadline__recall.is-warn`) | An at-risk row — a studied card whose predicted exam-day recall has fallen below 0.85 — was flagged by colouring the figure warn-orange (`$cfa-warn`) and **nothing else**: `recallCell()` returned the identical "62.1%" string for an at-risk and a healthy row, so the ONLY difference was the CSS `color`. A reader with a red-green colour vision deficiency (~8% of men) had **no cue** to which rows are at risk. Simulated dichromacy (Viénot severity-1) on the brand hues: the classic **pass↔warn hue pair collapses** — CIE76 ΔE **84 → 15 under protanopia** (>65% of the separation lost) — the canonical reason hue-only status is unsafe. (Honest: the specific warn-vs-ink pair in this table keeps its *luminance* separation, so severity is bounded to a Level-A compliance gap, not a luminance collapse — but 1.4.1 is a binary bar and the redundant cue is required.) | **FIXED (iter 46)** — a redundant NON-colour cue so the at-risk state survives with no colour: a **shape marker "▲"** rendered before the figure (new pure `isAtRisk()` / `riskMarker()` helpers) + a visually-hidden screen-reader label "at risk:" (`RISK_LABEL` via a `.cfa-deadline__sr` clip-rect). New cards never carry it; the warn colour is kept for sighted users (defence in depth). Shared engine + payload untouched. |

**Verification:** `ts/lib/cfa/pages/deadline.test.ts` **7 → 10** (isAtRisk /
riskMarker / RISK_LABEL) and `ts/lib/cfa/contrast.test.ts` **21 → 26** — a new
"use-of-color audit (WCAG 2.1 SC 1.4.1)" block: a CVD-simulator sanity check,
the **asserted** pass/warn collapse (ΔE ratio < 0.35 under protanopia), the
honest warn/ink retention (> 0.6), a FIX check (the page renders `riskMarker` +
`RISK_LABEL` + `.cfa-deadline__sr`) and a **regression guard** (deadline.ts
keeps the shape-based cue). New e2e gate `ts/tests/e2e/cfa_deadline_colorcue.test.ts`
(green vs the REAL backend, seeded): every warn cell ALSO carries the ▲ marker
(count == warn count), healthy rows carry none. Full CFA vitest **41/41**;
`./ninja check:svelte check:typescript check:eslint` all green. Genuine
before/after (same seeded deck, stash-isolated, scrolled to the at-risk rows) +
`colorcue-audit.txt` under `desktop-ui/pass-3-colorcue{,-before}/`. **Honesty:**
the CVD simulation is *computed* (linear-RGB dichromacy matrices → CIE76 ΔE), no
vision model, no AI.

## Pass 3 — MOBILE (ruthless, pixel-level): accessibility / contrast

Same ruthless lens as the desktop Pass-3 audit, applied to the CFA Android
tokens: a *measured* WCAG 2.1 audit (ratios computed from the compiled
resource values, not by eye). It found the mobile sibling of the desktop
finding — a warm-accent-as-small-text accessibility defect the earlier passes
missed.

### M-P3-1 — Warm brand accent fails WCAG AA as small text (the audit finding)

| ID | Severity | Where | Critique | Fix |
|----|----------|-------|----------|-----|
| M-P3-1 | MAJOR (accessibility) | Readiness eyebrow (11sp), Config eyebrow (11sp), Config exam countdown (13sp), nav-drawer tagline (12sp) | The warm brand accent `cfa_accent` (#DA5C01) was colouring small readable **text** in four TextViews, yet only reaches **3.81:1 on white** and **3.78:1 on the navy drawer** — below WCAG AA's 4.5:1 normal-text bar (it does not even clear the 3:1 large-text floor comfortably). The desktop design system already avoids this exact trap (`Eyebrow.svelte` uses the AA-safe `$cfa-mm-green` #007e56, not the orange accent); mobile had copied the accent onto text directly and never caught it. | **FIXED (iter 44)** — parity-safe (iter-26/43 pattern: add a new token, never change the accent's value — it stays correct for the FAB tint / outlined-button ripple / progress indicator, none of which are small text). Two AA-safe accent-**text** tokens added to `res/values/cfa.xml`: **`cfa_accent_ink` #A84500** for LIGHT backgrounds (white 5.97:1 / cfa_surface 5.50:1) and **`cfa_accent_on_navy` #F0894A** for the navy drawer (5.74:1). Note: darkening (like accent_ink) *reduces* contrast on navy, so the navy drawer needs a *brighter* warm tint — hence two tokens. Repointed the 4 TextViews. |

**Verification:** `AnkiDroid/src/test/java/com/ichi2/anki/cfa/CfaContrastTest.kt`
(**10 tests, green**) — computes WCAG contrast from the real compiled `R.color`
values, asserts AA for every CFA text token on its background, **documents why
the raw accent fails** (pins the finding so the accent can't be "fixed" by
quietly brightening the FAB), asserts the two new tokens clear AA, asserts the
fix stayed warm-orange (R>B by ≥60, not a grey collapse), and a **regression
guard** that parses the three layout XMLs and fails if `cfa_accent` ever returns
as a TextView `textColor`. Green: CFA unit tests, `lintVitalFullRelease`,
`ktlintCheck`, `installFullDebug`. Device-observable before/after on
`emulator-5554` (stash-isolated) + a FAIL→PASS swatch proof under
`AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-3{,-before}/` + `contrast-audit.txt`.
**Honesty:** GPT-4o vision critic still unavailable (no `OPENAI_API_KEY`); the
ratios are *computed*, which is stronger than a vision opinion for this defect.

### M-P3-2 — Exam Readiness score cards & topic rows fragment for TalkBack (screen-reader audit)

The ruthless lens escalates from colour/contrast (M-P3-1) into assistive-tech
semantics: the flagship Exam Readiness screen was audited for a NON-sighted
(TalkBack) user.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| M-P3-2 | MAJOR (accessibility) | `CfaExamReadinessActivity` — the 3 honest score cards + every per-topic recall row | Cards & rows are built programmatically as **separate sibling `TextView`s** in a plain `LinearLayout` with **no accessibility grouping**, so each `TextView` is its own accessibility node. TalkBack announces disconnected swipes and the **name↔number relationship is lost**: a topic row reads "Alternative Investments" … (swipe, unrelated) … "no data"; a score card fragments into "MEMORY" / "Awaiting reviews" / "\<reason\>". **WCAG 2.1 SC 1.3.1 Info and Relationships (A)** and **SC 4.1.2 Name, Role, Value (A)**. | **FIXED (iter 47)** — new pure helpers `CfaAccessibility.kt` (`topicRowContentDescription`, `scoreCardContentDescription`; singular/plural "review(s)"; hero-override does not leak the verbatim reason) build ONE coherent phrase per card/row. `CfaExamReadinessActivity` sets `contentDescription` + `ViewCompat.setScreenReaderFocusable(view, true)` on each card/row container and `importantForAccessibility=NO` on every inner `TextView`. Presentation/semantics only — scores, RPC, abstain rule and the visible pixels are unchanged. |

**Verification:** `AnkiDroid/src/test/java/com/ichi2/anki/cfa/CfaAccessibilityTest.kt`
(**7 tests, green**) locks the pure label builders + a **source-parsing
regression guard** asserting the activity groups cards & rows and hides
≥5 inner fragments. **Device-observable** on `emulator-5554` via
`uiautomator dump` (the a11y tree is the honest artifact — a screen-reader fix
changes no pixels): BEFORE the only non-empty `content-desc` is "Navigate up";
AFTER every card and topic row carries a single coherent `content-desc`
("Alternative Investments: no recall data yet", "Memory: awaiting reviews.
not enough data: 22 graded reviews (need 200)…"). Stash-isolated before/after
dumps + the (unchanged) screen under `AnkiDroid:
proof/gnhf-speedrun/mobile-ui/pass-3/` (`a11y-tree-readiness-{before,after}.xml`,
`05-readiness-a11y-after.png`, `a11y-audit.txt`). Green: CFA unit tests,
`ktlintCheck`, `lintVitalFullRelease`, `installFullDebug`.

### M-P3-3 — Exam-date box is a false affordance (interaction / touch-target audit)

The ruthless lens escalates again — from what a control *says* (M-P3-2) to
whether a control that *looks* interactive actually *is*. The Exam Config screen
was audited as a returning learner reaching to set their date.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| M-P3-3 | MAJOR (usability / accessibility) | `CfaExamConfigActivity` / `activity_cfa_exam_config.xml` — the exam-date box `cfa_config_date_value` | The date box is styled as a **filled input** (surface bg, 14dp padding, 18sp navy) so it reads as a tappable date field — but it was an **inert `TextView`**: no click handler, no role, empty `content-desc`. The ONLY control that opened the picker was a **separate secondary "Pick date" button** below it. So the obvious target did nothing and the user had to hunt for a second control; a TalkBack user heard only static text. **Nielsen #2 (match system↔real world) / #6 (recognition > recall); Material date-input convention; WCAG 2.1 SC 4.1.2 (Name, Role, Value) & 2.5.5 (Target Size).** | **FIXED (iter 48)** — the box IS the control now: `clickable`+`focusable`, `minHeight=48dp` (Material/WCAG 2.5.5 touch target), a `?attr/selectableItemBackground` ripple foreground, a trailing navy-tinted `calendar_single_day` affordance; tapping it opens the `MaterialDatePicker`. The redundant "Pick date" button (and its orphaned string) removed → exactly one date affordance. New pure `examDateFieldContentDescription()` gives TalkBack a coherent control label + action. Interaction/presentation only — `CfaExamConfig` persistence + countdown untouched. |

**Verification:** `CfaAccessibilityTest.kt` **7 → 11 tests, green** (3 pure
`examDateFieldContentDescription` cases + a source/layout regression guard that
asserts the box is clickable/focusable/48dp/ripple, the "Pick date" button id is
gone from both files, and the activity wires the click + the a11y label).
**Device-observable** on `emulator-5554`, stash-isolated real debug builds:
BEFORE the box is `clickable=false` with an empty `content-desc` and a "Pick
date" button is present (`pass-3-before/05-exam-config-inert-field-before.png`,
`exam-config-a11y-before.xml`); AFTER the box is `clickable=true` with
`content-desc="Exam date, not set. Double-tap to choose your exam date."`, no
"Pick date" button, and **tapping it opens the picker** ("July 2026" / Cancel /
OK) — `pass-3/05-exam-config-tappable-field-after.png`,
`06-exam-config-tap-opens-picker-after.png`, `exam-config-a11y-after.xml`,
`affordance-audit.txt`. Green: CFA unit tests, `ktlintCheck`,
`lintVitalFullRelease`, `installFullDebug`.

---

**Pass 3 COMPLETE — both apps.** Desktop has **3** ruthless findings (D-P3-1 text
contrast, D-P3-2 non-text/control-boundary contrast, D-P3-3 use-of-colour/CVD),
mobile has **3** (M-P3-1 accent-as-text contrast, M-P3-2 screen-reader grouping,
M-P3-3 false-affordance/touch-target) — all MAJOR, all FIXED, each backed by a
measured/scientific method (computed contrast ratios, CVD ΔE simulation,
accessibility-tree dumps, source/layout guards) with committed passing tests and
genuine before/after evidence. **No BLOCKER or unresolved MAJOR remains in any
of the three escalating passes on either app.**

---

## Pass 4 — critique of the post-Pass-3 surfaces (Concept Map, native Readiness)

The Concept Map tab (desktop + mobile) and the native desktop Exam-Readiness
state were built **after** "Pass 3 COMPLETE" was declared, so they had never
faced a critique pass. Pass 4 opens on the newest desktop surface and holds it
to the same give-up/abstain honesty bar as the rest of the app.

### D-P4-1 — Concept-Map side panel fakes a 0% score for an abstaining node (honesty / give-up-rule audit)

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-1 | MAJOR (honesty / abstain rule) | `CfaConceptMapPage.svelte` — the side-panel mastery gauge (`.cfa-map__gauge`) | The node map itself honours the give-up rule (an abstaining node with no evidence stays **gray**, `EMPTY_FILL`), but the **side panel contradicted it**: the gauge rendered `width: {active.pct ?? 0}%`, so selecting an abstaining node (`pct === null`, e.g. Fixed Income / Derivatives before any review) drew a **flat empty bar identical to a genuine 0% score**. A user reading the panel could not tell "not enough evidence yet" apart from "you scored zero" — the exact fake-confidence the objective's give-up/abstain rule forbids. | **FIXED (iter 7)** — the fill `<i>` is now drawn **only when `active.pct !== null`**; an abstaining node instead gets an `is-nodata` track: a neutral diagonal **"awaiting evidence" hatch** (`repeating-linear-gradient`), honestly distinct from both a flat empty-0% and a partial turquoise fill. The gauge also gained proper `role="progressbar"` + `aria-valuetext` ("No data yet — awaiting evidence" vs "N% mastered") so screen readers get the same distinction. Presentation only — the engine, scores, and node fills are unchanged. |

**Verification:** `ts/lib/cfa/pages/conceptmap.test.ts` **22 → 23 tests, green**
(new `D-P4-1` source-parsing regression guard: the `active.pct ?? 0}%` fallback
is gone, the fill is gated behind `#if active.pct !== null`, and the
`is-nodata` track + style exist). `just cfa-conceptmap-test` green;
`npx svelte-check` 0 errors. **Before/after evidence:**
`proof/concept-map/panel-gauge-abstain-fix.{html,png}` — BEFORE an abstaining
node and a true-0% node render as identical flat empty bars; AFTER the
abstaining node shows the neutral hatch while the true-0% node stays a flat
empty bar, making the two states unmistakably distinct.

### D-P4-2 — CFA top-bar nav gives no "you are here" indication (product-nav / orientation audit)

Pass 4 continues on the native shell. The desktop top bar was rebuilt as a CFA
product nav (Home / Study / Ethics / Concept Map / Readiness) — but it was
audited as a user who has just clicked "Readiness" and is trying to confirm
where they are.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-2 | MAJOR (orientation / product-feel) | `qt/aqt/toolbar.py` `_centerLinks` + `qt/aqt/cfa_chrome.py` `_toolbar_css` — the CFA nav tabs | Every CFA tab rendered as an identical muted `.hitem` link with **no active-state marker**. Landing on the native Home / Concept Map / Readiness screens (built in iters 1/6), the top bar looked byte-identical regardless of which section you were in — the objective's explicit "reads as stock Anki, not a purpose-built product" clunk. Stock Anki's toolbar has no active-tab concept, so the CFA fork inherited a row of undifferentiated links; a UWorld-grade product nav must always show the current section. **Nielsen #1 (visibility of system status); no orientation cue.** | **FIXED (iter 9)** — the current section is now a filled **accent pill** (white text on the warm accent, a clear selected-segment treatment) via a new `.hitem.is-active` chrome style. `Toolbar._update_active_cfa_tab` maps the main-window state → its tab id (`cfaHome`/`cfaConceptMap`/`cfaReadiness`) and sets `is-active` + `aria-current="page"` on that tab, clearing it on every other tab. It runs from `redraw()` **and** a `gui_hooks.state_did_change` subscription, so leaving a CFA screen for the deck list or a study session never leaves a stale pill lit. Pure presentation — no scores, routing, or navigation logic change. Study/Ethics launch into the shared overview/review flow (no dedicated state) so they carry no persistent pill, documented as a known limit. |

**Verification:** `qt/tests/test_cfa_active_tab.py` (**7 tests, green**, added to
`just cfa-desktop-shell-test` → **51 tests green**): the state→tab map, the
active-highlight JS for a CFA state, the null-clear for a non-CFA state, the
`state_did_change` transition (into and out of a CFA state), `redraw()`
refreshing the tab, and source guards that the chrome styles a distinct
`.hitem.is-active` accent pill and the toolbar registers the state hook.
**Rendered evidence:** `proof/friday/desktop-shell/active-tab-readiness.{html,png}`
renders the REAL `cfa_chrome._toolbar_css()` over the actual nav ids with
Readiness marked exactly as `_eval_active_cfa_tab` would — the screenshot shows
"Readiness" as a filled orange pill while Home / Study / Ethics / Concept Map
stay muted navy links.

### D-P4-3 — Desktop Concept Map is missing the on-node hover tooltip (spec-fidelity / cross-platform-parity audit)

Pass 4 continues on the Concept Map, this time auditing it against the approved
interactive spec (`.lavish/concept-map-spec.html`) AND its own mobile twin,
since the objective demands the map be "identical on phone and desktop."

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-3 | MAJOR (spec fidelity / parity / discoverability) | `CfaConceptMapPage.svelte` — the map SVG | The approved spec (`showTip`) AND the shipped mobile asset (`concept_map.html`) both draw an **on-node hover tooltip** — a navy chip showing the node's **name + "% mastered"** right at the cursor. The desktop component had **no tooltip**: hovering a node only updated the **far-away side panel**. This is worst for the 20 **unlabelled subsection nodes** (only the 10 sections + CFA carry persistent labels), so a user hovering a subsection saw its name nowhere near their eyes — they had to look away to the panel to learn which node they were even on. The objective explicitly requires "**Hover a node → its name + how full it is (%)**"; the spec provides it co-located; desktop violated both spec fidelity and phone/desktop parity. | **FIXED (iter 10)** — added the spec/mobile tooltip verbatim: a `computeTip(node)` geometry helper (prefer-above, drop-below-if-clipping, `name.length*8.6+26` width) driven reactively by **hover/focus (`hotId`), never by a pinned selection** — exactly the spec's `enter`/`leave` semantics. It renders a navy `#122B46` chip with a white 15px name and a bright-turquoise `#4CE0D8` "% mastered" line, honouring the give-up rule (an abstaining node reads **"no data yet"**, never a fake 0%). The `<g>` is `aria-hidden` because the node's own `aria-label` already announces the same phrase (no double read). Also works on keyboard focus (a bonus over the spec). Pure presentation — the engine, scores, node fills and side panel are unchanged. |

**Verification:** `ts/lib/cfa/pages/conceptmap.test.ts` **23 → 24 tests, green**
(new `D-P4-3` source guard: the tooltip is driven by `hotId` not a pinned
select, emits both a name and a "% mastered"/"no data yet" line, and the group
is `aria-hidden`). `just cfa-conceptmap-test` green; `npx svelte-check` 0
errors/0 warnings. **Rendered evidence:** `proof/concept-map/hover-tooltip.{html,png}`
overlays the tooltip — computed with the SHIPPED `computeTip` formula — onto the
REAL engine SVG for two nodes: an unlabelled subsection reads **"Credit / 63%
mastered"** and an abstaining subsection honestly reads **"Real Estate / no data
yet"**, both positioned above the disc without clipping — byte-for-byte the
navy-chip / turquoise-% treatment the mobile asset and the approved spec show.

### D-P4-4 — Concept-Map SVG orphans its focusable nodes from screen readers (accessibility / ARIA-conflict audit)

Pass 4 escalates on the Concept Map from what a sighted user sees (D-P4-1 gauge,
D-P4-3 tooltip) to what a **screen-reader** user can reach. The map was audited
with the a11y tree as the artifact, since the fix changes no pixels.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-4 | MAJOR (accessibility / ARIA conflict) | `CfaConceptMapPage.svelte` — the map `<svg>` container | The desktop made every one of the 31 nodes a **focusable** `role="button"` `tabindex="0"` (a keyboard-a11y enhancement over the spec) — but the SVG container kept the spec's `role="img"`. `role="img"` tells assistive tech to present the SVG as a **single flat image and prune its accessibility subtree**, so those focusable node buttons become **reachable by Tab yet invisible to screen readers** — the classic focusable-but-not-in-the-a11y-tree conflict. A keyboard+SR user Tabs onto "Ethics" and hears nothing; the map's whole interactive value (name + % per node) is silent. The spec/mobile use `role="img"` safely because THEIR nodes are not focusable; only the desktop introduced the conflict. **WCAG 2.1 SC 4.1.2 (Name, Role, Value, A) & SC 1.3.1 (Info & Relationships, A).** | **FIXED (iter 11)** — the container is now `role="group"` (accessible name unchanged: "Interactive CFA concept mastery map"). `group` gives the visualization a name **and** exposes the interactive node buttons, so every focusable node's `aria-label` ("Ethics: 63% mastered", "Real Estate: No data yet") is announced. Pure semantics — no pixel, engine, score, or fill change. |

**Verification:** `ts/lib/cfa/pages/conceptmap.test.ts` **24 → 25 tests, green**
(new `D-P4-4` source guard: the `<svg>` open tag carries `role="group"`, never
`role="img"`, keeps its `aria-label`, and the nodes remain focusable
`role="button"` `tabindex="0"`). `just cfa-conceptmap-test` green; `svelte-check`
0 errors on the component. **Accessibility-tree evidence** (the honest artifact —
the fix changes no pixels): `proof/concept-map/a11y-role-fix.{html,png,-tree.txt}`
render the EXACT structure (a focusable `role="button"` node inside the map SVG)
under both roles and dump the browser a11y tree — BEFORE (`role="img"`) the tree
has only `image "Interactive CFA concept mastery map"` and the node button is
**absent/pruned**; AFTER (`role="group"`) the tree exposes
`button "Ethics: 63% mastered"`, proving the focusable node is now reachable by
assistive tech.

### D-P4-5 — Concept-Map pinned node has no exit (user control & freedom / keyboard operability audit)

Pass 4 escalates on the Concept Map from what a user can *see* (D-P4-1 gauge,
D-P4-3 tooltip, D-P4-4 a11y tree) to what a user can *do* — auditing it as
someone who clicked a node to read its explanation and now wants to leave.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-5 | MAJOR (user control & freedom / keyboard operability) | `CfaConceptMapPage.svelte` — the node selection (`selId` / `onSelect`) | Clicking a node **pinned** its explanation by a one-way `selId = n.id`, and there was **no way to unpin it**: clicking the same node again did nothing new, there was no Escape handler, and no background-click clear. The only "escape" was to click a *different* node — you could never return to the calm hover-driven overview / centre summary. For a keyboard user it was worse: after Enter-to-pin, focus sat on the node with **no key** that dismissed the panel — a trapped pinned state. **Nielsen #3 (user control & freedom — always provide an "emergency exit"); no keyboard operable exit.** | **FIXED (iter 12)** — `onSelect` now **toggles**: `selId = selId === n.id ? null : n.id`, so clicking (or Enter/Space on) a pinned node unpins it and returns to the hover/centre default. **Escape** unpins from anywhere via a `<svelte:window on:keydown>` listener AND the on-node key handler, so a keyboard user is never trapped even if focus has moved. The exit is made discoverable in the lede copy ("click it again or press `Esc` to unpin"). Pure interaction — the engine, scores, node fills, tooltip and panel content are unchanged. |

**Verification:** `ts/lib/cfa/pages/conceptmap.test.ts` **25 → 26 tests, green**
(new `D-P4-5` source guard: the toggle-off `selId === n.id ? null : n.id`, the
`svelte:window` Escape listener + `onWindowKey`, the on-node `Escape` branch,
and the discoverability hint). `just cfa-conceptmap-test` green; `svelte-check`
0 errors/0 warnings. **Device-observable functional evidence** (the fix is
interaction, not pixels): `proof/concept-map/unpin-fix.html` ports the SHIPPED
selection handlers verbatim and is driven in a real browser —
`selId` goes `null → topic:ethics` (click pins) `→ null` (click same node again,
toggle unpins), and a separate node pins then **Escape** returns it to `null`
(`unpin-fix-pinned.png` / `unpin-fix-unpinned.png`).

### D-P4-6 — Desktop "tab-to-fill" has no visible affordance inviting the Tab press (discoverability / feature-parity-with-objective audit)

Pass 4 turns from the Concept Map to the card **editor** — the home of the
headline "tab-to-fill the back" AI feature. The objective states it precisely:
"when the front has content, **an affordance invites the user to press Tab** to
auto-generate the back."

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-6 | MAJOR (discoverability / objective fidelity) | `qt/aqt/cfa_tab_fill.py` — the desktop card editor | `Tab` **was** already bound (a capture-phase `keydown` → `pycmd(cfaTabFill)`, `_TAB_JS`), and there was an "AI Fill" button + `Ctrl+Alt+F` shortcut — but **nothing in the UI told the user Tab does anything**. The button tooltip named only `Ctrl+Alt+F`; the module docstring even wrongly claimed "we leave `Tab` doing its normal job." So the feature was a hidden Easter egg: a user either never discovered it, or was *surprised* when Tab silently drafted a back they meant to type. The objective's required in-context invitation ("an affordance invites the user to press Tab") was **absent**. | **FIXED (iter 14)** — a live, **contextual in-field affordance**: whenever AI is on and exactly one of front/back is filled (mirroring `fill_note`'s bidirectional rule), a subtle hint "✦ Press `Tab` to generate this with AI" renders **inside the empty field**, right where the generated text will land. It keys off the editor's own live `.rich-text-editable.empty` class (light DOM — no shadow-root traversal), so it appears/vanishes **in real time** as the user types and disappears the instant the field gains content or AI is switched off (`_HINT_JS` + a `MutationObserver`; field indices + AI state pushed from Python on `editor_did_load_note` via a new `should_invite` pure rule). On-palette: warm CFA accent `#da5c01` sparkle, muted `#4d5c6d` text, a body-font (never monospace) key-cap. `aria-hidden` since the button tooltip already announces the same phrase. The button tooltip now also names `Tab` first. The stale docstring was corrected. AI-off safe: the hint never appears and nothing calls out. |

**Verification:** `qt/tests/test_cfa_tab_fill.py` **32 → 40 tests, green**
(`just cfa-tab-fill-test`): new guards on `should_invite` (invite only when
exactly one side filled; never when AI off; blank-ish front counts as empty),
the `_HINT_JS` (keys off `.rich-text-editable`/`empty`/`data-index`, renders the
Tab invitation, uses a `MutationObserver`, is `aria-hidden`, stays on the CFA
palette with no monospace), `_on_editor_init` injecting the hint scaffolding,
`_configure_hint` pushing `configure(front,back,aiOn)` (with the AI-on/off and
single-field-note cases), and `register()` wiring `editor_did_load_note`. Also
made the pre-existing `..._ai_off_leaves_note_untouched` test tolerant of a
working local `.env` key (iter 2). **Device-observable evidence:**
`proof/tab-fill/affordance.html` reconstructs the real editor DOM
(`.fields > .field-container[data-index] > … > .rich-text-editable.empty`) and
loads the **shipped** `_HINT_JS` verbatim, driven in a real browser:
`configure(0,1,true)` → the hint appears **in the back field**
("✦ Press Tab to generate this with AI", `aria-hidden=true`, `affordance-on.png`);
typing into the back (drop `.empty`) → hint **vanishes**; `configure(0,1,false)`
(AI off) → hint **vanishes**; and the **reverse** (back filled, front empty) →
hint appears **in the front field**.

### D-P4-7 — Ethics AI grade is silently un-attributed when AI is off / inconsistent across the two cards (honesty / provenance / objective-fidelity audit)

Pass 4 turns to the ethics reviewer — the other headline AI feature. The
objective is explicit about provenance: the grade must "**say ai failed if that
call failed, or if the case turned off then say deterministic**." Both ethics
card templates violated it, in two different ways.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-7 | MAJOR (honesty / provenance / objective fidelity) | `cfa/ethics_pairs/templates/front.html` + `passage_front.html` — `renderAiGrade()` | The reveal shows an "AI feedback" block **only when the LLM actually graded** (`source === "ai"`). Every other path was mis-handled: (a) when AI grading is **toggled OFF** (`error === "ai_off"`) `front.html` stayed **silent** — a user could not tell whether the shown grade came from the LLM or the offline rule-based grader (the objective's required "say deterministic" was absent); (b) `passage_front.html` was worse — it returned silently on **both** the off-state **and** a genuine AI failure, so a failed AI call looked identical to a successful one; (c) `front.html`'s Android proxy path **swallowed a failed fetch** (`.catch(function(){})`), so a proxy outage on phone showed no "AI failed" cue at all. Two sibling cards, two different silent behaviours — inconsistent, and neither met the objective's honest-attribution bar. | **FIXED (iter 15)** — `renderAiGrade()` in **both** templates now renders three explicit, visually-distinct states: (1) `source === "ai"` → the navy "AI feedback" block (unchanged); (2) `error === "ai_off"` (or no error) → a calm **muted "Deterministic"** badge + "AI grading is off — showing the offline (deterministic) grade" on a neutral `is-off` surface; (3) any other error → a **warn "AI failed"** badge + "⚠ AI grading failed — showing the deterministic grade. Reason: …" on a warn `is-warn` wash. `front.html`'s Android `.catch` now reports `proxy_unreachable` instead of swallowing it. New `style.css` `.cfa-ai.is-off` / `.cfa-ai.is-warn` (+ badge + night-mode) variants make the three states unmistakable. Presentation-only — the deterministic grade, the byte-mirrored JS graders, scores and the abstain rule are all unchanged. |

**Verification:** `cfa/ethics_pairs/tests/test_ai_provenance.py` (**5 stdlib
tests, green**, in `just cfa-test`) source-parses BOTH templates + `style.css`:
each template says "Deterministic" on `ai_off`, says "AI failed" (naming
`no_api_key` / `unparseable_response` / `llm_client_unavailable`) on a real
failure, the two old silent-return guards are **gone**, the Android `.catch`
reports `proxy_unreachable` (no bare swallow), and the CSS carries distinct
`is-off` / `is-warn` (+ night-mode) provenance styles. Full ethics suite
**126 passed, 3 skipped**. **Device-observable evidence:**
`proof/ethics-provenance/provenance.{html,png}` renders each of the three
`renderAiGrade` branches **verbatim** against the REAL `style.css` — a navy
"AI FEEDBACK" box, a muted "DETERMINISTIC" (AI-off) box, and a warm "AI FAILED"
warn box, all three visually distinct.

### D-P4-8 — Phone ethics card ignored the synced AI-grading toggle (honesty / provenance / cross-platform parity)

Pass 4 continues on the ethics reviewer, this time cross-platform. Iter 15/D-P4-7
made the grade say "Deterministic" when AI is off — but only on **desktop** (the
pycmd bridge is toggle-gated). The **phone** path in `front.html` fetched the AI
proxy **unconditionally on Android**, so with AI switched off the desktop said
*Deterministic* while the phone still called the LLM and rendered *AI feedback* —
the objective's "say deterministic when off" rule was violated on the phone.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-8 | MAJOR (honesty / provenance / parity) | `cfa/ethics_pairs/templates/front.html` (Android branch) + AnkiDroid reviewer | The card's `requestAiGrade` Android branch called `fetch(.../cfa/grade)` regardless of the synced `cfa_ai_enabled`/`cfa_ai_grading_enabled` toggle — the phone had no way to read col.conf from JS, so "AI off" never reached the card. | **FIXED (iter 19)** — AnkiDroid's reviewer (`AbstractFlashcardViewer.updateCard`) now prepends `window.CFA_AI_GRADING_ENABLED` from col.conf via a pure `CfaCardInject.withAiToggle`; `front.html` checks `=== false` **before** the fetch and renders the honest "Deterministic" (`error:"ai_off"`) state with **no network**. `undefined => on`, so older builds/desktop are unaffected. |

**Verification:** desktop `test_ai_provenance.py::test_mobile_grade_honours_the_synced_ai_toggle` green (full ethics suite **130 passed**); mobile `CfaCardInjectTest` (3) + `CfaAiClientTest` (16) green, main sourceset compiles. **Device-observable** (`AnkiDroid/proof/ethics-ai-toggle/gate-proof.{html,png}`, shipped gate driven in a real browser): `toggle=OFF → fetchCalls=0` + Deterministic box shown; `toggle=ON → fetchCalls=1`; `toggle=unset → fetchCalls=1` (back-compat).

### D-P4-9 — Deck study-intro (Overview) shipped as un-themed stock Anki (design-system consistency / "no un-themed stock-Anki screens" audit)

Pass 4 turns from the CFA-native surfaces (Concept Map, Readiness, editor,
ethics) to the shared **flow** surfaces. Auditing the app as a user who clicks a
deck or "Study" and lands on the deck study-intro: the CFA chrome hook
(`cfa_chrome.on_webview_will_set_content`) only re-skinned the top toolbar and
the deck list — the **Overview** webview between the deck list and the Reviewer
was never touched, so it rendered as pure stock Anki.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-9 | MAJOR (design-system consistency / product feel) | `qt/aqt/cfa_chrome.py` `on_webview_will_set_content` — the `Overview` stdHtml webview (`qt/aqt/overview.py`, `css/overview.css`) | The deck study-intro — the screen you land on every time you pick a deck or click **Study**, right before the Reviewer — shipped **100% stock Anki**: a plain sans-serif deck `<h3>`, a stock-**blue** "New" count (`.new-count` → `--state-new` #3b82f6, the exact same leak fixed on the deck list in D8-1), and the single primary CTA — the **"Study Now"** button (`#study` → `--button-primary-bg`, stock Anki blue) — with zero CFA identity on a white `--canvas` page. Between the navy CFA deck list and (on mobile) the navy Reviewer, this middle screen read as a jarring plain-Anki interruption — the objective's explicit "no visibly un-themed stock-Anki screens remain" clunk. | **FIXED (iter 20)** — added an `Overview` branch to `on_webview_will_set_content`: `_overview_css()` tints the page to the CFA `primary_soft`, sets the deck `<h3>` to the brand **serif** heading face in navy, retones the stock-blue **"New" count to brand navy** (parity with D8-1; Learn=red / Review=green count semantics left untouched), and restyles the **"Study Now"** CTA as a **brand-navy pill** with white text (mirroring the mobile reviewer "Show answer" navy decision, M8-1) — so this is the single primary action, unmistakably CFA. `_overview_eyebrow()` prepends a quiet centred accent **"ankiCFA · Level II · Study session"** eyebrow above the deck title. Additive presentation only via a public `gui_hooks` — no stock render code rewritten; the counts, scheduling, and "Study Now" wiring are unchanged. |

**Verification:** `qt/tests/test_cfa_chrome.py` **7 → 9 tests, green**
(`just cfa-chrome-test`): new guards that the `Overview` context gets the
`cfa-chrome-overview` style + the brand eyebrow prepended above the (centred)
deck title, that `_overview_css()` retones the `#study` CTA to brand navy and
the "New" count to navy, and that the learned Learn/Review count colours are NOT
touched. **Before/after evidence** (`proof/overview/overview-{before,after}.{html,png}`,
`just cfa-capture-overview`, screenshot via chrome-devtools-axi over the REAL
compiled `overview.css` so the stock-blue leaks + the exact `#study`/count
cascade are faithfully present): BEFORE a white page with a plain-sans title, a
**stock-blue "20" New count** and a **stock-blue "Study Now"** button; AFTER a
CFA-tinted page with an accent eyebrow, a **serif navy** deck title, a **navy**
New count (Learn=red / Review=green preserved), and a **navy pill "Study Now"**
CTA — one cohesive CFA study-intro.

### D-P4-10 — Reviewer answer bar (Show Answer + Again/Hard/Good/Easy) shipped as un-themed stock Anki (design-system consistency / "no un-themed stock-Anki screens" audit)

Pass 4 continues along the study **flow**. After D-P4-9 themed the Overview
study-intro, the very next screen — the one a user stares at on *every single
card* — is the Reviewer answer bar (`ReviewerBottomBar` bottom webview:
`Reviewer._bottomHTML` + `_showAnswerButton` + `_answerButtons`). It shipped as
**pure stock Anki**: native gray `<button>` elements (Edit / More / Show Answer /
Again / Hard / Good / Easy) on a plain bar. This is the single most-used surface
in a spaced-repetition app, and it read as plain Anki with no CFA identity.

| ID | Severity | Where | Finding | Fix |
|----|----------|-------|---------|-----|
| D-P4-10 | MAJOR (design-system consistency / product feel — most-used surface) | `qt/aqt/cfa_chrome.py` `on_webview_will_set_content` — the `ReviewerBottomBar` stdHtml webview (`qt/aqt/reviewer.py`, `css/reviewer-bottom.css`) | The reviewer answer bar rendered **100% stock Anki**: native OS-gray `<button>`s for Edit / More, the "Show Answer" CTA, and the Again/Hard/Good/Easy rating buttons, on a plain white bar. No brand type, no CFA palette, no primary-CTA emphasis, no rating cue — the most-studied screen in the product looked like vanilla Anki. | **FIXED (iter 21)** — added a `ReviewerBottomBar` branch to `on_webview_will_set_content` calling `_reviewer_bottom_css()`: the bar sits on the calm CFA page with a hairline `line` top rule; **Edit / More** become quiet transparent text buttons (accent on hover); the rating buttons become rounded **CFA chips** (hairline border → accent-soft hover) in the brand font; **"Show Answer" (`#ansbut`)** is the single **navy primary pill** CTA; the recommended/default answer (`#defease`) is a **filled navy pill** so the eye is guided to it; and **"Again" (`data-ease="1"`, always Again regardless of button count)** carries a quiet **fail-red caution border**. Other tiers stay neutral — deliberately NOT a traffic-light so it avoids the stock-addon look and the Good/Hard ambiguity a count-varying `data-ease` number would introduce. Additive presentation only via a public `gui_hooks` — no reviewer render code rewritten; the pycmd wiring, counts, and scheduling are unchanged. |

**Verification:** `qt/tests/test_cfa_chrome.py` **9 → 11 tests, green**
(`just cfa-chrome-test`): new guards that the `ReviewerBottomBar` context gets
the `cfa-chrome-reviewer-bottom` skin (body left intact), that `#ansbut` +
`#defease` are the navy primary pill, that `data-ease="1"` carries the fail-red
caution border, and that tiers 2/3 are NOT traffic-light-coloured.
**Before/after evidence** (`proof/reviewer-bottom/reviewer-bottom-{before,after}{,-q}.{html,png}`,
`just cfa-capture-reviewer-bottom`, screenshot via chrome-devtools-axi over the
REAL compiled `toolbar-bottom.css` + `reviewer-bottom.css` so the stock button
cascade is faithfully present): BEFORE a row of native gray OS buttons; AFTER
rounded CFA chips with a red-bordered "Again", a filled-navy "Good" (default),
and a navy-pill "Show Answer" — one cohesive CFA study surface.

### D-P4-11 — Session-complete ("Congratulations — finished") screen shipped as un-themed stock Anki (design-system consistency / "no un-themed stock-Anki screens" audit)

Pass 4 continues along the study **flow** past the Reviewer. After a learner
answers the last due card, the very next screen — the **reward moment** they see
at the *end of every completed study session* — is the congrats/"finished"
screen (`ts/routes/congrats/CongratsPage.svelte`, loaded by
`overview.py:load_sveltekit_page("congrats")`). Unlike the deck list, Overview
and reviewer bar (all re-skinned via the `cfa_chrome` stdHtml hook), this is a
**SvelteKit page** the chrome hook never reaches, so it had never been captured
or critiqued — and it shipped 100% stock Anki.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-11 | MAJOR (design-system consistency / product feel — end-of-session reward surface) | `ts/routes/congrats/CongratsPage.svelte` — the whole page | The session-complete screen rendered as **plain stock Anki**: a bare sans-serif `<h1>` ("Congratulations! You have finished this deck for now."), stock-**blue** `--fg-link` links ("unbury them" / "custom study"), and a `--border`-grey deck-description box on the bare `--canvas` — zero CFA identity on the screen that closes out every study session. Between the navy CFA Reviewer/answer-bar and the CFA Home the learner returns to, this end-of-flow screen read as a jarring plain-Anki interruption — the objective's explicit "no visibly un-themed stock-Anki screens remain" clunk, on a *high-frequency* surface. | **FIXED (iter 22)** — themed the page to the CFA design system: imports `$lib/cfa/theme.scss` (brand fonts + `:root` tokens) and wraps the content in `.cfa-app`; adds the brand **`<Eyebrow>` "ankiCFA · Level II · Session complete"** (AA-safe MM-green) over the heading; the `<h1>` is now the **brand serif in navy** (`$cfa-font-heading` / `$cfa-ink`); links are the warm **accent** (`$cfa-accent`, hover `$cfa-accent-hover`) instead of stock blue; and the whole block sits in a **calm CFA card** (hairline `$cfa-line`, 4px radius) with the deck-description in a `$cfa-surface` sub-card. Presentation-only — the scheduling logic (`congratsInfo` refresh, `buildNextLearnMsg`, review/new-limit messages) and the `bridgeLink("unbury")` / `bridgeLink("customStudy")` wiring are all untouched. |

**Verification:** new `ts/routes/congrats/congrats.test.ts` (**3 vitest tests,
green**, `just cfa-congrats-test`): asserts the theme + Eyebrow imports and the
brand eyebrow copy, that the stock `var(--fg-link)` / `border: 1px solid
var(--border)` hooks are **gone** and replaced by the CFA token module + serif
heading + accent links + CFA hairline, and a preservation guard that the
scheduling logic + both bridge links + `deckDescription` are untouched.
`npx svelte-check` **0 errors / 0 warnings** (1300 files); `eslint` clean on both
new files. **Before/after evidence** (`proof/congrats/congrats-{before,after}.{html,png}`,
screenshot via chrome-devtools-axi over the REAL `_tokens.scss` values so the
shipped styling is faithfully rendered): BEFORE a plain sans `<h1>`, stock-blue
links and a grey `--border` box on white; AFTER a green brand eyebrow, a serif
navy heading, warm-accent links, and a calm CFA card — one cohesive CFA
session-complete screen.

---

## Pass 4 — D-P4-12: the knowledge flashcard face was stock-Anki "Basic"

**Surface:** the CFA Level II knowledge card **face** shown during *Study by Exam
Priority* / *Study* — the single surface a candidate spends the **most** time on.

**How it was found:** auditing the deck builder (`tools/cfa/build_cfa_deck.py`)
showed all 711 knowledge notes were created on the stock **`Basic`** note type
(`col.models.by_name("Basic")`). The ethics cards have a bespoke CFA template,
but the 700+ knowledge cards inherited stock Anki's default note-type CSS —
`font-family: arial; font-size: 20px; text-align: center; color: black` — so the
highest-time-on-screen surface read as **plain Anki**, not a CFA product. Every
`cfa_chrome` re-skin (toolbar/deck list/Overview/answer bar) surrounds this card,
yet the card *content itself* was never branded.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-12 | MAJOR (design-system consistency / product feel — highest-time-on-screen surface) | The knowledge deck's note type (was stock `Basic`) | The flashcard face — front prompt and back answer — rendered in stock-Anki **centred Arial, black-on-white**, with a bare `<hr>` and unstyled source footer. Between the CFA navy answer bar below and the CFA chrome around it, the actual card a learner stares at all session read as stock Anki — the objective's "no visibly un-themed stock-Anki screens" clunk, on the *most-viewed* surface. | **FIXED (iter 29)** — added a **CFA-branded note type ("CFA Knowledge")** (`tools/cfa/cfa_notetype.py`) and pointed the deck builder at it. The card face is now the CFA design system: an accent **"ankiCFA · Level II" eyebrow**, the prompt as the **brand serif in navy** (`Source Serif 4` / `#122B46`, left-aligned, 1.6 line-height, matching every other CFA surface), a calm brand-line rule (`--cfa-line`) replacing the stock `<hr>`, a navy answer, and the named-source footer styled as quiet faint-ink. Full night-mode variants included. The CSS/templates live *in the note type*, so they **travel with the collection and the exported `.apkg`** — desktop, every synced device, and the phone import all get the identical CFA card with zero per-platform work. Fields (`Front`/`Back`), tags, exam-queue join key and memory score are unchanged; presentation-only. |

**Verification:** `just cfa-deck-test` (**54 passed**), incl. the new
`test_knowledge_cards_use_cfa_branded_notetype`: every knowledge card is on the
`CFA Knowledge` note type (none left on `Basic`), the note-type CSS carries the
CFA tokens (`--cfa-accent`, `--cfa-font-heading`, `.cfa-prompt`, `.cfa-source`),
the templates carry the eyebrow + serif prompt + answer structure, and
re-`ensure`-ing is idempotent (no duplicate note type). `.apkg` export verified
to carry the `CFA Knowledge` note type (mobile parity). **After evidence**
(`proof/knowledge-card/knowledge-card-after.{html,png}`, rendered via
chrome-devtools-axi over the note type's REAL compiled CSS from a real built
card): a warm accent eyebrow, a serif-navy prompt, a calm rule, a navy answer,
and a muted source line — one cohesive CFA card face.

---

## Pass 4 — D-P4-13: the note editor (host of the flagship tab-fill AI feature) was stock Anki

**Surface:** the desktop **note editor** webview — Add Cards, Edit Current, and
the Browse editor pane (all render via `Editor.setupWeb` → `stdHtml(context=self)`,
so the context class name is `Editor`).

**How it was found:** auditing `cfa_chrome.on_webview_will_set_content`, the CFA
chrome re-skins `TopToolbar` / `DeckBrowser` / `Overview` / `ReviewerBottomBar`
but had **no `Editor` branch** — so the editor rendered as pure stock Anki. This
is the surface that hosts the flagship **"Tab to complete the back" AI feature**
(`cfa_tab_fill.py`): a reviewer opening Add Cards to try the headline feature met
a plain-Anki screen (bare `--canvas`, lowercase sans field labels, a stock-blue
focus ring), directly contradicting "no visibly un-themed stock-Anki screens
remain" on a feature-critical surface.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-13 | MAJOR (design-system consistency / product feel — flagship-AI-feature surface) | The note editor webview (`Editor` context) | The editor shipped 100% stock Anki: field cards on a bare `--canvas`, plain-sans lowercase field labels ("Front"/"Back"), a stock-**blue** `--border-focus` ring, and grey field borders — zero CFA identity on the screen that hosts the tab-to-fill AI feature. | **FIXED (iter 36)** — added an `Editor` branch + `_editor_css()` to `cfa_chrome`: the editor sits on the calm CFA **page tint** (`--primary-soft #F3F6F8`, white field cards on top for editing legibility); field labels become quiet **CFA section labels** (navy-muted `#4D5C6D`, 700-weight, tracked uppercase, `fs_meta`); field cards get a **hairline CFA border** (`--line`); and a focused field glows the **warm CFA accent** (`#DA5C01`) instead of the stock-blue ring — matching the accent the tab-fill affordance already uses. Additive via the existing `webview_will_set_content` gui_hook; the editor DOM/body, rich-text content, toolbar icons and tab-fill wiring are all untouched. |

**Verification:** `just cfa-chrome-test` / `just cfa-desktop-shell-test` — 2 new
tests (`test_editor_gets_cfa_skin`, `test_editor_retones_labels_and_focus_to_cfa`,
13 in `test_cfa_chrome.py`): the `Editor` context gets the `cfa-chrome-editor`
skin with the body left intact, and the CSS retones `.label-name` to tracked
CFA caps, `.editor-field` to the hairline `--line` border and the
`:focus-within` ring to the CFA accent, on the `--primary-soft` page tint.
**Before/after evidence** (`proof/editor-chrome/editor-{before,after}.{html,png}`,
`tools/cfa/render_editor_chrome.py` — the shipped `_editor_css()` overlaid on a
faithful editor-DOM reconstruction over the real stock editor CSS variables):
BEFORE plain lowercase sans labels, a stock-blue focus ring and black text on a
grey canvas; AFTER tracked navy-muted labels, navy text, hairline CFA borders and
a warm-accent focus ring on the CFA page tint — one cohesive CFA editor.

---

## Pass 4 — D-P4-14: the main reviewer body is un-themed stock Anki

**Surface:** the **main reviewer webview** — the frame around every card during
Study (renders via `Reviewer._showQuestion/_showAnswer` → `web.stdHtml(context=self)`,
so the context class name is `Reviewer`). Distinct from the already-themed
`ReviewerBottomBar` (D-P4-10) answer bar.

**How it was found:** auditing `cfa_chrome.on_webview_will_set_content`, the CFA
chrome re-skins `TopToolbar` / `DeckBrowser` / `Overview` / `ReviewerBottomBar` /
`Editor` but had **no `Reviewer` branch**. The card CONTENT is CFA-branded (the
"CFA Knowledge" notetype CSS from iter 29 + the ethics templates), but the
surface AROUND the card — the reviewer page background and the type-in-answer
diff — was pure stock Anki: a bare-white body void, and the harsh stock
traffic-light type feedback (`.typeGood` bright-green `#afa`, `.typeBad`
bright-red `#faa`, `.typeMissed` grey `#ccc`), which clash badly with the CFA
design system on the highest-time-on-screen surface.

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-14 | MAJOR (design-system consistency / product feel — highest-time-on-screen surface) | The main reviewer webview (`Reviewer` context) | The study page had no CFA identity around the card: a bare-white body (so any card not painting its own background is a plain-white rectangle, unlike the CFA-tinted Overview/Editor), and the type-in-answer diff used the stock bright-green/bright-red/grey traffic-light blocks (`#afa`/`#faa`/`#ccc`) — jarring against the calm CFA palette. | **FIXED (iter 37)** — added a `Reviewer` branch + `_reviewer_css()` to `cfa_chrome`: the study page sits on the same calm CFA **page tint** (`--primary-soft #F3F6F8`) as Overview/Editor, scoped to `body:not(.nightMode)` so night mode keeps its dark `--canvas`; the type-in-answer diff is retoned to the CFA **pass/fail/neutral washes** (`.typeGood` → `--pass-soft #f0fdf4`, `.typeBad` → `--fail-soft #fef2f2`, `.typeMissed` → `--line #E7E9EC`) with brand-ink/muted text for legibility. Presentation-only and additive via the existing `webview_will_set_content` gui_hook; `#qa` card content is never touched, so the notetype CSS + ethics templates stay authoritative on the card itself. |

**Verification:** `just cfa-chrome-test` / `just cfa-desktop-shell-test` — 2 new
tests (`test_reviewer_gets_cfa_skin`, `test_reviewer_retones_page_tint_and_type_answer_feedback`,
15 in `test_cfa_chrome.py`): the `Reviewer` context gets the `cfa-chrome-reviewer`
skin with `#qa` left intact, and the CSS retones the body tint (light mode only)
and the three type-answer classes to the CFA washes with the stock `#afa`/`#faa`/`#ccc`
removed. **Before/after evidence** (`proof/reviewer-chrome/reviewer-{before,after}.{html,png}`,
`tools/cfa/render_reviewer_chrome.py` — the shipped `_reviewer_css()` overlaid on a
faithful reviewer-body reconstruction over the real stock reviewer CSS): BEFORE a
bare-white void with bright-green/red/grey traffic-light diff blocks; AFTER the
card sits on the CFA page tint with the diff shown in calm CFA pass/fail/neutral
washes — one cohesive CFA study surface.

---

## Pass 4 — D-P4-15: statistics screen (`GraphsPage.svelte`) was pure stock Anki

**Surface:** the Statistics report (opened via the Stats action / `stats.py`
`load_sveltekit_page("graphs")`). This is stock Anki's biggest reporting
surface, and it was the largest remaining **100%-stock-Anki SvelteKit page** —
a bare `--canvas` body void, stock `TitledContainer` card titles (default sans,
`--border` rules), and a stock `--canvas`/`--border` sticky range selector with
blue system radios. For a CFA exam-prep product, "how am I tracking" is a core
view, so a stock-Anki stats page reads as "Anki with a CFA tab."

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-15 | MAJOR (design-system consistency / product feel — the core progress surface) | The statistics screen (`GraphsPage.svelte`, `graphs` SvelteKit route) | No CFA identity: bare page canvas, stock card titles, stock blue range-selector radios/borders — the biggest un-themed stock-Anki surface left. | **FIXED (iter 38)** — themed `GraphsPage.svelte` to the CFA design system (mirroring the D-P4-11 congrats pattern): imports `$lib/cfa/theme.scss` + the brand `Eyebrow`, wraps the content in `.cfa-graphs.cfa-app` (CFA **page tint**), adds an `ankiCFA · Level II · Study statistics` eyebrow, and via **scoped** `:global` retones the graph card titles to **serif navy** on CFA hairline edges, the sticky range strip to the CFA **surface** tone with a CFA border, and the range radios/spinner to the **warm accent**. Presentation-only — the d3 charts, data query, `WithGraphData`, and `browserSearch` bridge are untouched; all retones are scoped under `.cfa-graphs` so shared `TitledContainer`/`InputBox` users elsewhere are never restyled, and the dark theme keeps its own tokens (card retone is `.container.light` only). |

**Verification:** `ts/routes/graphs/graphs.test.ts` — 3 source-parse tests
(theme + eyebrow + `cfa-app` wrapper present; CFA tokens used, scoped under
`.cfa-graphs`, no bare global `TitledContainer` override; charts/query/bridge
behaviour preserved), green alongside `congrats.test.ts`. `npx svelte-check`
passes 0 errors / 0 warnings across 1302 files. **Before/after evidence**
(`proof/graphs-chrome/graphs-chrome.{html,png}`): BEFORE a bare-white body with
stock sans card titles and blue system radios; AFTER the CFA page tint, a green
brand eyebrow, serif-navy card titles on CFA hairlines, and a CFA-toned range
strip with warm-accent radios — one cohesive CFA statistics surface.

---

## Pass 4 — D-P4-16: themed statistics page was reachable only from the menu bar

**Surface:** CFA top-bar navigation (`toolbar.py` `_centerLinks`) + the study
statistics screen (`GraphsPage.svelte`). D-P4-15 themed the graphs page to the
CFA design system, but it was still opened ONLY via a modal `NewDeckStats`
QDialog from Anki's menu bar — the CFA top-bar nav (Home / Study / Ethics /
Concept Map / Readiness) had NO Progress/Stats entry. For a CFA exam-prep
product, "how am I tracking" is a core, first-class view, so a themed report a
user can only find by hunting through the menu bar reads as "Anki with a CFA
tab" — the exact clunk iter 6 killed for Readiness (modal → native state).

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-16 | MAJOR (discoverability / product feel — a core progress surface had no place in the product nav) | CFA top-bar nav; the themed graphs page | The statistics screen was reachable only from the menu-bar `Statistics` action (a modal dialog); the CFA nav had no Progress entry, so the core "how am I tracking" view was undiscoverable from the product shell. | **FIXED (iter 39)** — added a native `cfaProgress` main-window state (`qt/aqt/cfa_progress.py`, mirroring `CfaReadiness`) that loads the themed `graphs` page into the MAIN webview, plus a **"Progress" top-bar tab** (`toolbar.py`) that `moveToState("cfaProgress")` and lights up the active-tab pill. The graphs page is self-contained (its own `RangeBox` scope/day-range + search), so it needs no dialog chrome; the page's `browserSearch:` bridge (click a bar → open Browser) is honoured by the state's `_link_handler`, matching the dialog. The menu-bar `Statistics` entry (which adds the deck chooser + Save-PDF) is untouched. |

**Verification:** `qt/tests/test_cfa_progress.py` — 4 tests (state exists +
dispatched + set up in `main.py`; toolbar exposes the `Progress` tab, active-tab
map, and native-state handler; the controller loads the `graphs` page; the
`browserSearch:` bridge opens the Browser filtered to the clicked cards).
`test_cfa_active_tab.py` map assertion updated to include `cfaProgress`. Full
`cfa-desktop-shell` suite green (73 passed); `ruff check` clean.

---

## Pass 4 — D-P4-17: Card Info was a 100%-stock-Anki surface

**Surface:** the Card Info screen — the shared `CardInfo.svelte` component behind
both `card-info/[cardId]` routes, opened from the reviewer **"More → Card Info"**
during Study and from the **Browser** sidebar. Every reviewer/deck-browser chrome
was re-skinned across iters 20–21/37–38, but the Card Info page itself was still
pure stock Anki: a bare white page, an **unstyled** key/value `stats-table`, and a
revlog whose review-kind colours were the stock traffic-light `--state-new`
(blue) / `--state-review` (green) / `--state-learn` (red). For a CFA exam-prep
product a card's review history ("how has THIS card gone") is a core detail view,
so a bare-Anki stats sheet reads as "Anki with a CFA tab."

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-17 | MAJOR (design-system consistency / product feel — a core per-card history surface) | Card Info (`CardInfo.svelte`) — stats table + revlog | No CFA identity: bare white page, unstyled stat key/value table, and a stock blue/green/red traffic-light revlog — the largest remaining un-themed SvelteKit surface in the Study flow. | **FIXED (iter 39)** — themed `CfaInfo` (mirroring the D-P4-15 graphs pattern): imports `$lib/cfa/theme.scss` + the brand `Eyebrow`, wraps the content in `.cfa-cardinfo.cfa-app` with a light-mode CFA **page tint**, adds an `ankiCFA · Level II · Card details` eyebrow, and via **scoped** `:global` retones the stat table to **serif-navy labels** on CFA **hairline** row rules (brand-ink values), the revlog column heads to serif-navy, and the stock traffic-light revlog kinds to CFA tones (learn → warm **accent**, review → **ink navy**, relearn → **fail-red**). Presentation-only — the stats query, the `Revlog` table, and the FSRS `ForgettingCurve` chart are untouched; every retone is scoped under `.cfa-cardinfo` so shared stats-table users elsewhere are never restyled, and the light page tint + revlog retones are guarded `:not(.nightMode)` so the dark theme keeps its own tokens. |

**Verification:** `ts/routes/card-info/card-info.test.ts` — 3 source-parse tests
(theme + eyebrow + `cfa-app` wrapper present; CFA tokens used, scoped under
`.cfa-cardinfo`, light-mode-guarded page tint, no bare global `stats-table`
override; the stats/revlog/forgetting-curve behaviour preserved), wired as
`just cfa-card-info-test`, green. `npx svelte-check` passes 0 errors / 0 warnings
across 1302 files. **Before/after evidence** (`proof/card-info/card-info.{html,png}`):
BEFORE a bare-white page with bold-sans stat labels and blue/green/red revlog;
AFTER the CFA page tint, a green brand eyebrow, serif-navy stat labels on CFA
hairline rules, and a CFA-toned revlog (navy Review / accent Learn / fail-red
Relearn) — one cohesive CFA card-history surface.

---

## Pass 4 — D-P4-18: Deck options (Study settings) was a 100%-stock-Anki surface

**Surface:** the deck-options dialog (`DeckOptionsPage.svelte`), opened from the
deck gear / preset editor. It is the scheduling + FSRS config a sophisticated CFA
candidate opens to tune their daily new/review load — a genuine part of the study
flow. Every reviewer/overview/editor/graphs/card-info chrome was re-skinned across
iters 20–21/36–39, but this dialog was still pure stock Anki: a **stock-blue Save
button**, **blue focus rings**, **blue links**, and **light-blue selected rows** —
so a core settings screen read as "Anki with a CFA tab."

| # | Severity | Element | Issue | Fix |
|---|----------|---------|-------|-----|
| D-P4-18 | MAJOR (design-system consistency / product feel — a core study-config surface) | Deck options (`DeckOptionsPage.svelte`) — Save button, focus, links, selected rows, section titles | No CFA identity: stock `--button-primary-bg`/`--border-focus`/`--fg-link`/`--selected-bg` blue throughout — the largest remaining un-themed SvelteKit surface in the study flow. | **FIXED (iter 40)** — wrapped the page in `.cfa-deckopts.cfa-app` with a brand `ankiCFA · Level II · Study settings` **Eyebrow**, and instead of per-control selectors **overrode the stock-blue design-token CSS vars in-scope** (`--button-primary-bg`/gradient → CFA **navy**; `--border-focus`/`--fg-link` → warm **accent**; `--accent-card` → navy; `--selected-bg` → **accent-soft**) so every descendant control — Save button, focus rings, links, selected preset row — adopts CFA colours at once, plus a light CFA **page tint** and serif-navy section titles. Presentation-only: the `ConfigSelector`, every option section, the preset-change wiring, and the addon `api` exports are untouched. Everything is scoped under `.cfa-deckopts.is-light` (gated `!$pageTheme.isDark`) so the dark theme keeps its own tokens and no other `TitledContainer`/`InputBox` user is restyled. |

**Verification:** `ts/routes/deck-options/deck-options-theme.test.ts` — 3 source-parse
tests (theme + eyebrow + `cfa-app` wrapper + `is-light` gate present; the five
stock-blue vars overridden to CFA tokens scoped under `.cfa-deckopts.is-light`;
the config-selector / option-section / addon-api behaviour preserved), wired as
`just cfa-deck-options-theme-test`, green. `npx svelte-check` passes 0 errors /
0 warnings across 1303 files. **Before/after evidence**
(`proof/deck-options/deck-options-theme.{html,png}`): BEFORE a blue Save button,
blue focus ring, blue link and light-blue selected row; AFTER a CFA navy Save
button, warm-accent focus ring + link, accent-soft selected row, a brand eyebrow,
and a serif-navy section title — one cohesive CFA settings surface.
