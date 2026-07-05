# Concept Map Screenshot Comparison Notes

Compared against:

- `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/desktop.png`
- `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/mobile.png`

## Matched

- Pearl-to-turquoise page wash, translucent app bar, liquid-glass hero, map stage, side panel, cards, soft highlights, and subtle shadows.
- Frozen hierarchy: center CFA readiness, 10 weighted section nodes, and subsection orbit with fixed organic geometry.
- Minimalist-at-rest map: labels remain on center/section nodes, subsection detail appears through hover/tap tooltip and pinned panel.
- Desktop layout preserves the frozen hero → map/panel stage → mechanic/hierarchy/AI/parity explanation sequence.
- Narrow widths keep the same feature and visual language, with stacked stage and restrained pan/pinch support instead of a separate simplified screen.

## Intentional Deviations

- The SVG container remains `role="group"` instead of the frozen static mock's `role="img"` because production nodes are focusable buttons; `role="img"` would hide them from assistive technology.
- The panel defaults to live overall CFA readiness from existing data instead of the mock's placeholder copy.
- Native Android/Kotlin source is not present in this checkout, so the implemented mobile pass is the shared Svelte page's Android-width experience rather than a separate native destination.
- Per-subsection fills inherit parent section evidence until subsection-level backend evidence exists; see `CONCEPT_MAP_BACKEND_GAPS.md`.
