# Perfect Feature: Concept Map Mastery Engine

Frozen at: 2026-07-05 15:37:35

## Source Of Truth

- Production reference HTML: `.lavish/perfect-feature.html`
- Original Lavish artifact: `.lavish/concept-map-spec.html`
- PDF packet: `.lavish/perfect-feature.pdf`
- Desktop screenshot: `.lavish/perfect-feature-desktop.png`
- Mobile screenshot: `.lavish/perfect-feature-mobile.png`

## Build Exactly This

This feature should be built as a new **Concept Map** page in both products:

- Desktop app: a first-class Concept Map tab/page, matching the frozen visual treatment and interaction model.
- Android app: a first-class Concept Map destination with the same hierarchy, map behavior, styling, and explanation panel.

No visual degradation is acceptable from the frozen reference. The production implementation should preserve the same pearl-to-turquoise liquid glass look, typography feel, spacing, hierarchy, node behavior, and explanation copy model.

## Core Feature

The Concept Map is the mastery engine. It is not a decorative graph.

- Center node: `CFA`, overall exam readiness.
- Orbit 1: the 10 CFA test sections.
- Orbit 2: subsections under each section.
- Node size: exam weight.
- Node fill: mastery, light gray to turquoise.
- Hover/tap: shows exact name and percent.
- Click/tap: pins a plain-English explanation and fastest next drill.
- AI behavior: explanations are batched when the tab opens so node taps are instant.
- AI-off behavior: templated explanations still work; map and drills remain usable.

## Visual Requirements

- Pearl/light background with turquoise depth.
- Liquid-glass panels with blur, translucent cards, soft white highlights, and subtle depth shadows.
- Turquoise is the mastery/progress semantic.
- Orange/gold is not the main surface color here; keep this page clean, pearl, and turquoise.
- The map is minimalist at rest. Detail appears on interaction.
- Desktop and Android should feel identical in feature behavior, with platform-appropriate layout only.

## Production Acceptance Bar

- The production page must visually match `.lavish/perfect-feature.html` as closely as native/web constraints allow.
- Desktop and Android screenshots should be compared against `perfect-feature-desktop.png` and `perfect-feature-mobile.png`.
- No stock Anki / AnkiDroid styling should appear on this page.
- No fallback graph/table experience unless the graph fails to render.
- No per-tap AI spinner; explanation payload should be precomputed/batched.
- If insufficient evidence exists, nodes stay gray and copy uses the give-up rule rather than fake precision.

## Source Code Snapshot

The exact source snapshot is saved separately at `.lavish/perfect-feature.html`. Keep it as the production reference.
