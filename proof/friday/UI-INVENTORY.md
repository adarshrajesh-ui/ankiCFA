# UI Inventory — every screen + state (both apps)

Phase B (SPEEDRUN-PLAN §4 step 1). The authoritative list of surfaces the
multi-pass UI/UX critique loop must capture and critique. Derived from the real
routes / Qt dialogs / Android activities in the two repos (not aspirational).

Legend for **Capture**: how each surface is screenshotted.

- `web` — SvelteKit page served by mediasrv at `http://127.0.0.1:40000/…`,
  driven by Playwright (`ts/tests/e2e/`), booted via `launch_anki_for_e2e.py`.
- `qt` — native Qt dialog/window, `screencapture -x` / `QWidget.grab()` offscreen.
- `adb` — Android emulator, `adb exec-out screencap -p`.

## Desktop (this repo)

| #   | Screen                                  | Route / entry point                                                                            | Capture | States to cover                                                                             |
| --- | --------------------------------------- | ---------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------- |
| D1  | **CFA Home** (native landing dashboard) | `/cfa-home` → `CfaHomePage.svelte`; `qt/aqt/cfa_home.py`                                       | web     | first-run empty/abstain (done p1); populated (ranges + Bayesian call); AI-on vs AI-off chip |
| D2  | **Exam Readiness**                      | `/cfa-readiness/{deckId}` → `CfaReadinessPage.svelte`; dialog `aqt/cfa.py:ExamReadinessDialog` | web     | abstain + full coverage map (done p1); populated ranges; empty (non-CFA) deck (done p1)     |
| D3  | **Exam Priority / Deadline**            | `/cfa-deadline/{deckId}` → `CfaDeadlinePage.svelte`; `aqt/cfa.py`                              | web     | with plan; no exam date set; empty deck                                                     |
| D4  | **Reviewer — Ethics minimal-pairs**     | Ethics deck card template (`cfa/ethics_pairs/*/front.html`)                                    | web/qt  | pre-attempt; both judgments + highlight; graded reveal (correct / partial / wrong)          |
| D5  | **Reviewer — standard CFA card**        | Anki reviewer chrome (re-skinned)                                                              | qt      | question; answer; ease bar                                                                  |
| D6  | **AI Settings**                         | `qt/aqt/cfa_ai_settings.py` dialog                                                             | qt      | master ON; master OFF (features gated); per-feature toggles                                 |
| D7  | **Connect / Sync / Logout**             | `qt/aqt/cfa_sync_connect.py`; toolbar Sync                                                     | qt      | logged-out (Connect); connecting/syncing; logged-in-as; error                               |
| D8  | **Deck browser** (CFA-skinned)          | main window deck list                                                                          | qt      | with CFA decks; empty                                                                       |
| D9  | **Deck config**                         | deck options SvelteKit page                                                                    | web     | default                                                                                     |
| D10 | **Stats**                               | stats page                                                                                     | qt/web  | with data; empty                                                                            |
| D11 | **Menus / toolbar / title bar**         | `aqt/cfa_chrome.py`, `cfa_style.py`                                                            | qt      | Home/Study/Ethics/Readiness nav + Sync                                                      |
| D12 | **First-run / language / profile**      | first launch                                                                                   | qt      | clean-machine (captured under A13)                                                          |
| D13 | **Loading / error states**              | any web route mid-load / RPC error                                                             | web     | spinner; RPC failure fallback                                                               |

## Mobile (`/Users/adarshrajesh/wed/AnkiDroid`, branch `gnhf/speedrun-mobile`)

| #  | Screen                          | Entry point                             | Capture | States to cover                                |
| -- | ------------------------------- | --------------------------------------- | ------- | ---------------------------------------------- |
| M1 | **DeckPicker** (native ankiCFA) | launch → `DeckPicker`                   | adb     | with CFA decks; counts; empty                  |
| M2 | **CFA Exam Readiness**          | nav drawer → `CfaExamReadinessActivity` | adb     | abstain (source=on-device); populated; offline |
| M3 | **Exam Priority**               | `CfaExamQueue` entry                    | adb     | with queue; empty                              |
| M4 | **Exam Config**                 | CFA config screen                       | adb     | set date; unset                                |
| M5 | **Reviewer**                    | card review                             | adb     | question; answer; ethics pair                  |
| M6 | **Nav drawer**                  | hamburger                               | adb     | open, CFA entries                              |
| M7 | **Sync / settings**             | sync icon; preferences                  | adb     | pending-upload dot; syncing; done; AI toggle   |
| M8 | **Empty / loading / error**     | fresh install; offline                  | adb     | first-run; airplane-mode (captured under M4)   |

## Pass tracking

Screens captured per pass live under
`proof/friday/gnhf-speedrun/desktop-ui/pass-N/` and
`…/mobile-ui/pass-N/`. Before/after pairs are kept across passes. Issues and
severities are logged in `proof/friday/UI-CRITIQUE-LOG.md`.
