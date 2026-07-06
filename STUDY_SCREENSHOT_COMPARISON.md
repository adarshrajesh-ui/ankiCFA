# Study Screenshot Comparison Notes

Compared against:

- `.lavish/perfect features/Study - Deck-First CFA Workspace/desktop.png`
- `.lavish/perfect features/Study - Deck-First CFA Workspace/mobile.png`

## Matched

- Pearl-to-turquoise background, sticky liquid-glass app bar, rounded hero, fast-create panel, deck grid, add-card panel, and footer note.
- Default deck workspace shows at most three deck cards and keeps the add-card composer secondary on desktop.
- Top tabs on the Study surface are exactly `Study`, `Concept Map`, `Readiness`, and `Sync`, with Study active.
- Mobile-width layout stacks the same hierarchy and keeps touch-friendly controls.

## Intentional Deviations

- Deck counts and labels come from the live Anki deck tree, so exact numbers can differ from the frozen mock.
- The quick-add composer opens existing Add Cards for the selected deck with the Basic note type selected instead of silently inserting the visible prompt/answer card. See `STUDY_BACKEND_GAPS.md`.
- Native Android/Kotlin source is not present in this checkout; Android fidelity is implemented as the shared Svelte mobile-width Study surface.
