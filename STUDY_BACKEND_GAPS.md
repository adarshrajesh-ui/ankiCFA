# Study Backend Gaps

## Dynamic inline quick-add draft payload

- Current behavior: Study opens native Add Cards with the selected deck and selects the stock `Basic` note type when available. If `Basic` is missing, it leaves the existing/default note type untouched.
- Required capability for the exact inline composer: pass a structured draft payload from Svelte containing deck id, prompt, answer, tags, and optional note type.
- Why existing data is still insufficient: the current bridge command is string-only (`add` / `add:<deckId>`), so the visible composer text cannot be transferred into Add Cards without a structured bridge payload.
- Minimal API/payload shape: `{ deckId: number, noteTypeId?: number, fields: Record<string, string>, tags: string[] }`.
- Deterministic placeholder acceptable temporarily: yes. The UI keeps the lightweight composer visible and routes `Add card draft` to Add Cards for the selected deck with `Basic` selected, without silently inserting fake cards.
- Blocked visual/interaction requirement: one-click creation of the exact visible prompt/answer draft from inside the Study workspace.

## CFA-topic deck creation preset beyond shipped deck bundle

- Current behavior: the single Study creation action uses the existing idempotent CFA seed path, loading the shipped `CFA Level II` deck and `CFA::Ethics Pairs` deck where sources are available, then selecting the Ethics deck.
- Required capability beyond this: create an arbitrary new deck from a CFA topic preset, optionally including default tags/note type.
- Why existing data is insufficient: Anki's existing deck creation dialog creates named decks, while the shipped seeder creates the authored CFA/Ethics bundle; neither exposes a topic-picker payload for custom new decks.
- Minimal API/payload shape: `{ topic: string, deckName: string, parentDeckId?: number, defaultTags: string[], noteTypeId?: number }`.
- Deterministic placeholder acceptable temporarily: yes. Study now prefers the premade CFA/Ethics deck path instead of blank deck creation.
- Blocked visual/interaction requirement: true one-step custom CFA-topic deck creation from the Study workspace.
