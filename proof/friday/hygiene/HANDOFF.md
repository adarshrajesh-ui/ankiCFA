# Hygiene Workstream — HANDOFF / cross-scope notes

Branch: `friday/hygiene` (worktree `/Users/adarshrajesh/AlphaWeek2/ankiCFA-hygiene-wt`).
These are items that touch OTHER workstreams' scope, or that I deliberately did
NOT change. Nothing here was edited by me outside my scope.

## 1. One-passage retirement — BLOCKED on W3 (ethics), NOT actioned

Increment 3 asked me to retire stale one-passage refs _iff_ W3 has landed the
removal on `origin/main`. It has **not**:

- `origin/main` still ships and even enhances the one-passage surface:
  - `73bfea57b fix(cfa): add desktop "Study Ethics (One-Passage)" action seeding CFA::Ethics Passages (#10)`
  - `be9a21449 feat(cfa): restyle ethics one-passage card ... markmeldrum.com look (#12)`
  - `126a29823` bundles + renders the one-passage card on device (F7).
- The only retirement lives on the concurrent `friday/ethics` branch, unmerged:
  `0b6a0c389 friday/ethics INC4: retire the one-passage duplication`.

Decision: per the protocol ("if W3 NOT landed, do NOT delete one-passage refs"),
I left every one-passage reference in docs/tests intact. **Action for the
orchestrator / W3:** once the ethics retirement merges to `origin/main`, retire
the stale one-passage rows/links in `docs/cfa/PLATFORM-MATRIX.md` (row "Ethics
one-passage deck + note-type"), `README.md` (the _Study Ethics (One-Passage)_
menu bullet), and any one-passage lines in `docs/cfa/*`.

## 2. Mobile native surfaces — cited to the fork PR, pending merge

`docs/cfa/PLATFORM-MATRIX.md` now records the fork's native mobile **Exam
Readiness** screen (three scores). Honest scope, verified against the mobile
workstream's own NOTES + on-device screencap (`inc2-readiness-populated.png`):

- Done + proven on `friday/mobile` (AnkiDroid fork, [Anki-Android PR #1]):
  native Exam Readiness (Memory/Performance/Readiness + ranges + abstain +
  per-topic). Scores are a **deterministic on-device scorer** — the screen is
  literally labeled "Source: on-device (deterministic)" — because the shared
  `computeCfaScores` RPC is not exposed in the engine yet.
- **In progress / NOT claimed shipped:** native Study-by-Exam-Priority action
  (mobile Inc 3), on-device exam-config editor (Inc 4), minimal-pairs on device
  (Inc 5). Left as forward-looking caveats only.
- Cross-scope ask (engine owner): expose `computeCfaScores` as a read-only RPC so
  mobile scores become 🟢 shared-engine instead of an on-device fallback.

## 3. "20-card" — no literal default exists; documented the real behavior

Inc 2 asked to document "20-card = the exam-priority default fetch limit". There
is **no literal 20** anywhere in code: the exam-priority queue returns a capped
weakest-first _fetch_ — desktop `fetch_limit` 50 (`mediasrv`) / 200 (`aqt.cfa`),
mobile `MAX_SESSION_CARDS = 100` (`CfaExamPriorityActivity`). The deck itself is

> 200 authored cards (711). I documented the deck-size-vs-fetch-limit distinction
> in `tools/cfa/build_cfa_deck.py`'s docstring (and README, Inc 4) rather than
> asserting a false "20".

## 4. Shared-tree / stash hygiene (for whoever cleans up)

- The main tree (`ankiCFA`) carries the **sync** agent's uncommitted `justfile`
  change (adds `cfa-syncserver` / `cfa-sync-dedup-test` recipes). NOT mine; I
  restored it after briefly parking it to enter my worktree. Left intact.
- Out-of-scope `tools/cfa/serve_cfa_pages.py` kept reappearing in my worktree
  from concurrent activity; preserved in `stash@{...}` ("...serve_cfa_pages...")
  and reverted before each gate run. NOT staged/committed by me.
- CONCURRENCY: a concurrent agent ran `git reset --hard origin/main` in my
  worktree mid-run (reflog), wiping uncommitted copies once. Mitigated by
  committing + pushing each increment promptly.

## 5. Pre-existing, out-of-scope `just check` failures (NOT mine) — blocking full green

A full `just check` in a clean `friday/hygiene` worktree (Rust: **556 tests
pass**) still fails on lint debt that is **already committed in `origin/main`**
by other workstreams' PRs — none of it in my scope, none introduced by me:

- `check:ruff` — `tools/cfa/serve_cfa_pages.py:58` **I001** (import block un-sorted).
  Committed in `origin/main` (PR #21); also the file the sync agent keeps
  reordering. Explicitly on my NEVER-COMMIT list, so I cannot fix it.
- `check:format:dprint` — three markdown/mjs files dirty in `origin/main`:
  - `cfa/ui/reference/capture_app.mjs` (PR #22)
  - `cfa/ui/reference/app/verify-ethics-crossplatform-NOTES.md` (PR #18)
  - `proof/fixes/p1/NOTES.md` (PR #17)

These predate my branch (verified via `git log origin/main -- <file>` +
`ruff`/`dprint` on the committed blobs). **Action:** the owning workstreams (or a
repo-wide `just fix-fmt`, which touches non-scope files) should format them; I
left them untouched per the "only your scope" rule. My six in-scope failures are
fixed and my own files are ruff/dprint clean (`proof/friday/hygiene/inc1-after.txt`,
`final-check-summary.txt`).
NOTE: two lint issues I _did_ introduce — an unformatted `test_cfa_deadline_dialog.py`
(ruff format) and my own dprint-dirty `NOTES.md`/`HANDOFF.md` — were caught by the
full `just check` and fixed in commit-fixup (see NOTES.md Inc-1 addendum).
