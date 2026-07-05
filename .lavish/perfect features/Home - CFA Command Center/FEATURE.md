# Home - CFA Command Center

Frozen at: 2026-07-05 16:23:32

## Source Of Truth

- Approved Lavish artifact: `.lavish/home-screen.html`
- Frozen source: `.lavish/perfect features/Home - CFA Command Center/source.html`
- Desktop screenshot: `.lavish/perfect features/Home - CFA Command Center/desktop.png`
- Mobile screenshot: `.lavish/perfect features/Home - CFA Command Center/mobile.png`
- PDF packet: `.lavish/perfect features/Home - CFA Command Center/feature.pdf`

## What Was Approved

The approved Home screen is a desktop-first CFA command center in the same pearl-to-turquoise liquid glass language as the frozen Concept Map. The screen avoids marketing language, avoids generic deck-browser framing, and focuses on the work the learner should do today.

## Feature Scope

Build this as the desktop Home screen first, then adapt the same concept to Android after desktop perfection.

Primary navigation/tabs for the desktop concept:

- Home
- Study
- Concept Map
- Readiness
- Sync

Sync remains a tab. If the user clicks Sync while disconnected, production should show a connect/account flow instead of assuming a connected state.

## Core Screen Structure

- App bar with ankiCFA identity and the core tabs.
- Hero: `Today’s work`, with concise next-action copy.
- Primary action: `Begin priority session`.
- Secondary actions: `Open Concept Map`, `View weak areas`.
- Metric chips: days to exam, graded reviews, topic coverage, AI explanations.
- Priority risk card with exam-weighted weak areas.
- Concept Map preview card with interactive sphere map.
- Recommended session card.
- Maintenance session card.

## Concept Map Preview Behavior

The Home preview is not a static decoration. It should preview the full Concept Map feature while staying compact.

- Structure mirrors the Concept Map freeze: CFA center, section nodes orbiting it, subsection nodes beyond, and connection lines.
- Same sphere look as the frozen Concept Map.
- Scroll/trackpad over the map moves through the sphere field.
- Pinch zoom supports zoom in/out.
- Nearest sphere becomes active.
- Major section spheres show concept names directly on the circle.
- Active subsection grows and shows its concept name directly on the circle.
- Hovering any circle updates the detail chip.
- Detail chip shows priority, cards due, and prerequisite/dependency guidance.
- Clicking a concept changes the detail chip into a `Cards Due: <concept>` destination state, representing navigation to that concept’s filtered due-card queue.

## Visual Requirements

- Pearl/light background with turquoise depth.
- Liquid glass cards, app bar, chips, and map surface.
- Soft white highlights and subtle shadows.
- No stock Anki / AnkiDroid blue.
- No motivational/marketing copy.
- Home should feel useful and calm: next work, weak areas, concept map, sessions.
- Current screen scale is intentionally about 25% larger than the earlier draft. Preserve that larger visual weight.

## Desktop Production Notes

- Use `source.html` as the pixel reference for desktop.
- The Home screen should launch quickly and not depend on remote AI to render.
- Concept Map preview data can be deterministic/templated at first, but should eventually use the same concept graph data as the full Concept Map page.
- The priority session button should route to the Study / priority queue screen.
- Clicking Concept Map preview or `Open Concept Map` should route to the full Concept Map screen.

## Android Production Notes

- Do not implement phone first. Desktop is the canonical design source for this concept.
- When adapted to Android, preserve the same Home information hierarchy, but stack cards vertically.
- The mini Concept Map should remain interactive if practical; otherwise make the full Concept Map one tap away and preserve the due/need hover/tap semantics.

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
