# Study - Deck-First CFA Workspace

Frozen at: 2026-07-05 17:10:22

## Source Of Truth

- Feature name: Study - Deck-First CFA Workspace
- Approved Lavish artifact: `.lavish/study-screen.html`
- Frozen source: `.lavish/perfect features/Study - Deck-First CFA Workspace/source.html`
- Desktop screenshot: `.lavish/perfect features/Study - Deck-First CFA Workspace/desktop.png`
- Mobile screenshot: `.lavish/perfect features/Study - Deck-First CFA Workspace/mobile.png`
- PDF packet: `.lavish/perfect features/Study - Deck-First CFA Workspace/feature.pdf`

## Known User Decisions

- Reduce screen clutter so the Study surface starts with the work the learner can act on immediately.
- Show only up to three deck cards in the default deck workspace.
- The Study tab must make deck creation easy.
- Deck cards must show CFA decks and make studying or adding cards easy.
- Keep the top tabs: Study, Concept Map, Readiness, Sync.
- Preserve the premium pearl/turquoise liquid glass UI.
- Do not include `Open source node`, `FRA source node`, or `source node` concepts.

## Desktop And Android Production Scope

Desktop is the canonical implementation target for this freeze. Android must adapt the same deck-first workspace and visual language after desktop fidelity is achieved, preserving the hierarchy and interaction model within phone constraints.

Production scope includes the Study screen surface only: the liquid glass app bar, hero, fast deck creation panel, deck card workspace, quick add composer, and footer note shown in `source.html`.

## Visual Requirements

- Match `source.html` as the pixel reference for layout, hierarchy, typography feel, color, spacing, glass treatment, and card scale.
- Keep the pearl background, turquoise depth, soft highlights, rounded glass panels, and calm premium CFA study tone.
- Preserve the deck-first composition: hero actions above a three-card deck grid with the add-card panel beside it on desktop and stacked on Android.
- Keep stock Anki and AnkiDroid styling off this feature surface.
- Avoid adding extra content, cards, explanations, or source-node concepts that increase clutter.

## Interaction Requirements

- `Create new deck` and `Create CFA deck` must make deck creation immediately accessible from the Study tab.
- `Study deck` must start studying the selected CFA deck.
- `Add cards` and quick-add controls must make adding cards to a CFA deck immediate without leaving the deck workspace.
- The add-card composer must stay lightweight and secondary to the deck list.
- Top tabs must remain Study, Concept Map, Readiness, and Sync, with Study active.
- Android interactions should preserve the same destinations and priorities using stacked, touch-friendly controls.

## Screenshots And Packet

- Desktop screenshot: `.lavish/perfect features/Study - Deck-First CFA Workspace/desktop.png`
- Mobile screenshot: `.lavish/perfect features/Study - Deck-First CFA Workspace/mobile.png`
- Packet source: `.lavish/perfect features/Study - Deck-First CFA Workspace/packet.html`
- PDF packet: `.lavish/perfect features/Study - Deck-First CFA Workspace/feature.pdf`

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
