# Concept Map - Mastery Engine Liquid Glass

Frozen at: 2026-07-05 15:42:34

## Source Of Truth

- Approved Lavish artifact: `.lavish/concept-map-spec.html`
- Frozen source: `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/source.html`
- Desktop screenshot: `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/desktop.png`
- Mobile screenshot: `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/mobile.png`
- PDF packet: `.lavish/perfect features/Concept Map - Mastery Engine Liquid Glass/feature.pdf`

## What Was Approved

The approved feature is the Concept Map mastery engine rendered as a pearl-to-turquoise liquid glass UI. The user explicitly preferred this Concept Map spec over the broader workflow/product boards and asked that it be built exactly with no visual degradation.

## Feature Scope

Build this as a first-class **Concept Map** page in both products:

- Desktop ankiCFA: a first-class Concept Map tab/page.
- Android ankiCFA / AnkiDroid fork: a first-class Concept Map destination with the same core behavior and visual language.

The feature is the product core: learning intelligence for CFA, not a deck-browser decoration.

## Core Interaction Model

- Center node: `CFA`, overall readiness.
- Orbit 1: the 10 CFA test sections.
- Orbit 2: subsections under each test section.
- Node size: exam weight.
- Node fill: mastery, light gray to turquoise.
- Hover / tap preview: show node name and mastery percent.
- Click / tap pin: show plain-English explanation and fastest next drill.
- AI explanations: batched when the tab opens so interactions are instant.
- AI-off mode: templated explanations still work.
- Give-up rule: insufficient evidence stays gray; do not fake precision.

## Visual Requirements

- Pearl/light surface foundation.
- Turquoise mastery semantics.
- Liquid glass cards, map surface, and side panel.
- Soft white highlights, subtle shadows, and translucent depth.
- Minimalist at rest; detail appears only through interaction.
- Typography feel: IBM Plex Sans + Source Serif 4 from the frozen artifact.
- The map should remain fixed and memorable, not a random re-layout each load.

## Desktop Production Notes

- Use the frozen `source.html` as the visual reference.
- Preserve app-bar placement, stage proportions, map/panel relationship, hierarchy explanation sections, AI batching explanation, and phone/desktop parity section.
- The desktop page should support hover, click, and scroll/zoom affordances without degrading the map clarity.

## Android Production Notes

- Use the same data model and hierarchy as desktop.
- Use tap instead of hover, with optional pinch-to-zoom and pan for the outer subsection orbit.
- Keep the same pearl/turquoise liquid glass language.
- The phone should not become a simplified or stock Android screen; it should feel like the same feature adapted to mobile.

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
