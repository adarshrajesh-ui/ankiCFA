# Readiness Screenshot Comparison Notes

Compared against:

- `.lavish/perfect features/Readiness - Exam Risk Console/desktop.png`
- `proof/friday/gnhf-speedrun/desktop-ui/pass-2/02-cfa-readiness-populated.png`

## Matched

- Pearl-to-turquoise liquid-glass page wash, sticky app bar, rounded hero, score-side panel, risk cards, topic evidence card, action plan, and footer note.
- Top tabs on the Readiness surface are exactly `Study`, `Concept Map`, `Readiness`, and `Sync`, with Readiness active.
- Memory, Performance, and Readiness remain three separate score ranges and show `No score` when the payload abstains.
- The hero keeps the pass/abstain framing, readiness range, evidence counts, and explicit caveat that the local model is not validated against real CFA exam outcomes.
- Topic evidence exposes topic weight, reviewed coverage proxy, graded evidence, recall ranges, and visible weak/uncovered styling.

## Intentional Deviations

- Counts, ranges, topics, and risk ordering come from the live `getCfaExamReadiness` payload, so exact frozen mock values can differ.
- The Forgetting Watchlist is a topic-level proxy until card-level fade-risk rows are exposed; see `READINESS_BACKEND_GAPS.md`.
- `Open latest mock review` and `Schedule full mock` route to the existing deadline/readiness planning flow until mock metadata exists; see `READINESS_BACKEND_GAPS.md`.
- The frozen folder did not include `mobile.png` or `feature.pdf` at implementation time, so desktop fidelity is canonical and Android/mobile screenshot comparison remains a follow-up when those artifacts are added.

## Verification Note

- `just cfa-capture-populated` rendered the Readiness route and the Readiness E2E assertion passed, producing `proof/friday/gnhf-speedrun/desktop-ui/pass-2/02-cfa-readiness-populated.png`.
- The same recipe still exits non-zero because its preceding Home test expects legacy `.cfa-stat` selectors on the Home page; that failure is outside the Readiness route.
