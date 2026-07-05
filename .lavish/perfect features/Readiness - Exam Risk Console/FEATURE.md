# Readiness - Exam Risk Console

Frozen at: 2026-07-05 17:35:33

## Source Of Truth

- Feature name: Readiness - Exam Risk Console
- Approved Lavish artifact: `.lavish/readiness-screen.html`
- Frozen source: `.lavish/perfect features/Readiness - Exam Risk Console/source.html`
- Desktop screenshot: `.lavish/perfect features/Readiness - Exam Risk Console/desktop.png`
- Mobile screenshot: `.lavish/perfect features/Readiness - Exam Risk Console/mobile.png`
- PDF packet: `.lavish/perfect features/Readiness - Exam Risk Console/feature.pdf`

## Known User Decisions

- Readiness is the next core desktop screen after Home, Study, and Concept Map.
- The screen must be remade as an Exam Risk Console, not a generic analytics dashboard.
- It must answer: "Am I ready to pass, and what should I do next?"
- Keep the top tabs: Study, Concept Map, Readiness, Sync, with Readiness active.
- Preserve the premium pearl/turquoise liquid glass UI already approved for the product.
- Keep the screen restrained and focused; avoid overcrowding or stock Anki styling.
- Add an area that shows exactly what the learner is about to forget and lets them pull those cards out for maximum retention.
- Use three separate scores: Memory, Performance, and Readiness, each shown as a range. Do not collapse them into one blended number.
- When evidence is thin, show an honest abstain / no-score state with a clear reason instead of a fake number.
- Show coverage and evidence counts: graded reviews, first exposures, topics covered, topic weights, reviewed coverage, graded evidence, and recall ranges.
- The readiness hero must include a pass/fail call or abstain state, range/CI framing, and a caveat that the model is not validated against real exam data.
- Score cards must explain what each score measures: recall durability, new-question performance, or projected readiness.
- Weak and uncovered high-weight topics must be visible.
- The screen must work offline and with AI off; AI may explain results but the same local engine must produce scores or honest abstain states.

## Desktop And Android Production Scope

Desktop is the canonical implementation target for this freeze. Android must later adapt the same Readiness concept, hierarchy, scoring model, evidence display, retention watchlist, and liquid glass visual language within phone constraints.

Production scope includes the Readiness screen surface only: liquid glass app bar, exam-risk hero, separate score cards, major risk drivers, topic coverage/evidence table, forgetting watchlist, and next-action plan shown in `source.html`.

## Visual Requirements

- Match `source.html` as the pixel reference for layout, hierarchy, typography feel, color, spacing, glass treatment, and card scale.
- Preserve the calm pearl-to-dark-turquoise liquid glass atmosphere with soft depth, rounded cards, and restrained premium CFA copy.
- Maintain the separation between Memory, Performance, and Readiness score ranges.
- Keep weak/uncovered flags visible without turning the surface into a dense spreadsheet.
- Preserve the compact Forgetting Watchlist and its retention-pull action as a first-class readiness feature.
- Keep stock Anki and AnkiDroid styling off this feature surface.

## Interaction Requirements

- `Start risk-reduction session` starts the recommended readiness plan.
- `Run readiness drill` launches a readiness-specific diagnostic drill.
- `Open latest mock review` opens the latest mock evidence.
- `Pull retention queue` creates or opens the queue of cards predicted to fade soon.
- `Begin 35-minute plan` launches the composed next-action plan.
- `Schedule full mock` schedules or opens mock exam planning.
- Top tabs must remain Study, Concept Map, Readiness, and Sync.
- Android interactions should preserve the same actions using stacked, touch-friendly controls.

## Scoring And Evidence Requirements

- Memory score measures scheduled recall durability and predicted forgetting risk.
- Performance score measures graded vignette/new-question execution under exam pressure.
- Readiness score measures projected pass readiness from coverage, memory, and graded evidence.
- Scores must be ranges, not over-precise single values.
- If evidence is insufficient, production must show `No score` or an abstain state and state why.
- Coverage must expose topic weight, reviewed coverage, graded evidence, and recall range.
- Readiness must include the caveat that the model is not validated against real CFA exam outcomes.
- Scores must be computed locally and work offline with AI disabled.

## Screenshots And Packet

- Desktop screenshot: `.lavish/perfect features/Readiness - Exam Risk Console/desktop.png`
- Mobile screenshot: `.lavish/perfect features/Readiness - Exam Risk Console/mobile.png`
- Packet source: `.lavish/perfect features/Readiness - Exam Risk Console/packet.html`
- PDF packet: `.lavish/perfect features/Readiness - Exam Risk Console/feature.pdf`

## Production Acceptance Bar

- Production must match `source.html` visually as closely as platform constraints allow.
- Desktop and Android must preserve the same concept, hierarchy, typography feel, colors, spacing, and interaction model.
- Screenshots must be compared against `desktop.png` and `mobile.png`.
- No stock Anki / AnkiDroid styling may appear on this feature surface.
- Any intentional deviation must be documented with rationale and approved before implementation.

## Files In This Freeze

- `source.html` - frozen approved source.
- `desktop.png` - desktop screenshot of the frozen source.
- `mobile.png` - mobile screenshot of the frozen source.
- `packet.html` - printable packet source.
- `feature.pdf` - PDF packet with screenshots and source reference.
- `FEATURE.md` - this production contract.
- `manifest.txt` - generated artifact manifest.
