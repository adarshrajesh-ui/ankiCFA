# Cross-platform verification — CFA one-passage ethics card (Meldrum restyle)

Branch `verify/ethics-crossplatform` (worktree `ankiCFA-wt-verify`), off `origin/main`
`b10f996cd`. Item under test: **PSG-01** (Priya / MNPI) — the flagship one-passage card.
Restyle merged as PR #12 (`be9a21449`). VERIFY-ONLY: no template/style edits.

## Screenshots (this dir)

- `verify-ethics-desktop-front.png` / `-desktop-back.png` — 2000x1520 / 2000x1200 (2x)
- `verify-ethics-android-front.png` / `-android-back.png` — 1080x2400 (real device)

## Capture method — HONEST

### Desktop = harness render (Blink), NOT the live Qt window

Rendered the REAL `passage_front.html` / `passage_back.html` + `style.css` with **headless
Google Chrome** via the repo's own `tools/cfa/render_ethics_restyle.py` (same tool that
produced the committed `ethics-restyle-after-*.png`). Blink is the same engine as the
desktop AnkiWebView (Qt WebEngine = Chromium/Blink), so this is a faithful desktop render.
I did NOT drive the live `just run` Qt window (deck-nav + window-screencap GUI automation
would stall this lightweight check); labeled harness-vs-live per instructions. The BACK is
rendered from a seeded fully-correct `localStorage` payload (the harness's normal method).

### Android = REAL emulator, GENUINE attempt

Emulator `ankidroid_cfa` (`emulator-5554`, Android 14, 1080x2400), AnkiDroid
`com.ichi2.anki.debug`, System WebView **Chrome/113.0.5672.136**.

- The on-device deck still had the PRE-restyle templates (on-device notetype css=11 070 B,
  none of the restyle/font markers). I rebuilt the current deck (`just cfa-mobile-package`,
  byte-identical templates to origin/main) AND, to render the current restyle
  unambiguously, injected origin/main's restyled `qfmt`/`afmt`/`css` (css=104 191 B, with
  `data:font/woff2` + Source Serif 4 + IBM Plex Sans) into the on-device notetype via pylib,
  isolated PSG-01, and studied it live.
- FRONT: real reviewer screencap.
- BACK: a GENUINE fully-correct attempt, driven through the WebView DevTools (CDP) by
  clicking the actual DOM — verdict `Unethical`, the two gold-phrase token spans
  (`[24,28]`, `[42,49]`), then `Check` (`rootCorrect="1"`, 2/2 found) — then AnkiDroid's
  own "Show answer". `verify-ethics-android-front.png` is the fresh front; the boxed-green
  highlights + selected verdict were captured mid-flow (front-reveal) as proof of a real
  (not seeded) attempt.

## Fonts ACTUALLY LOAD on BOTH platforms (measured, not eyeballed)

Via `document.fonts` + DOM width probes at 120px:

|                              | Source Serif 4                                                      | IBM Plex Sans                                       |
| ---------------------------- | ------------------------------------------------------------------- | --------------------------------------------------- |
| Android WebView (Chrome 113) | `loaded`, check=true, 1243px vs 1235px generic-serif → **distinct** | `loaded` w400+w500, 1162px vs 1152px → **distinct** |
| Desktop Blink (Chrome 150)   | `loaded`, check=true, 1243px vs 1080px generic-serif → **distinct** | `loaded`, 1162px vs 1147px → **distinct**           |

Source Serif 4 = **1243px** and IBM Plex Sans = **1162px** on BOTH → the same bundled
data-URI faces render identically cross-platform. The @font-face data URIs work in
AnkiDroid's WebView. (On the BACK page Source Serif 4 reports `unloaded` — expected: the
back template uses IBM Plex Sans for all its text, so the serif face is never requested
there. The serif is exercised by the FRONT question hero.)

## BLUNT CRITIQUE — scores /10 on Meldrum fidelity

**Desktop (harness/Blink): 8.5/10.** Serif question hero (Source Serif 4), IBM Plex Sans
body, navy `#122B46` ink, flat hairline card, green uppercase cluster over-line, 100px pill
CTA. Reads calm and Meldrum-adjacent. Gaps: (1) pure-white canvas + cool `#f1f5f7`-ish
passage panel — Meldrum's warmth comes from a **cream** canvas (`~#f2ede4`) which the card
does not adopt, so it's cooler/flatter than the site. (2) The captured CTA is the **grey
disabled** state (no verdict picked yet); it only becomes the green pill once complete —
first impression is a dead grey button. (3) Type scale is restrained vs Meldrum's large
display serif.

**Android (real device): 7.5/10** for the same CARD (near-identical), minus 1 for the
**experience**: the card is wrapped in AnkiDroid's loud **bright-blue** app bar + deck-count
strip + dark "Show answer"/rating bars, which clash hard with the calm Meldrum palette. The
card itself is faithful; the surrounding chrome is not (and is outside the card's control).

**Fonts load?** YES on both (proven above).
**Layout breakage / clipping / wrong weights / missing styling?** None on either. Verdict
buttons, over-lines, pill CTA, passage panel, back reveal (governing-standard pill + serif
standard + serif rationale + ✓/~/✗ tiers) all render correctly. No clipping; portrait just
wraps the passage to more lines.

**Desktop ↔ Android parity: HIGH.** Same templates/CSS/fonts → same green cluster pill,
same serif question, same passage panel, same verdict buttons, same 100px pill CTA, same
back reveal. Fonts measure identically. Only real divergences: (a) AnkiDroid native chrome
vs the harness's bare card; (b) width/scale (1080px portrait wraps more than the 1000px
desktop shot); (c) desktop back seeded vs Android back genuine — both land on the identical
"fully correct" reveal.

## Prioritized fixes for true cross-platform parity

1. **Adopt Meldrum's cream canvas** (`.card` bg ~`#f2ede4`, warm panel tint) so both
   platforms match the site's warmth instead of cool white. (Biggest fidelity lift.)
2. **CTA first impression** — give the disabled "Check answer" a subtler outlined/ghost look
   (or a soft green tint) instead of solid grey, so the pill reads as brand even before it's
   enabled.
3. **Android chrome** — can't restyle AnkiDroid's bars from the card, but a themed reviewer
   (dark/neutral toolbar) or a top card gutter would reduce the blue-clash; note as an
   app-level follow-up, not a card fix.
4. **Bump the display serif scale** on the question hero to echo Meldrum's larger hero type.

None of the above are rendering BUGS — the restyle is correct and cross-platform. They are
fidelity refinements.
