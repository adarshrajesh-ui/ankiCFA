# Study Backend Gaps

## Inline quick-add draft prefill

- Required capability: open Add Cards with a structured draft payload containing deck id, prompt, answer, tags, and optional note type.
- Why existing data is insufficient: the current GUI flow can open Add Cards and preselect a deck, but the Study page cannot safely create or prefill an exam-style draft from Svelte without reaching into editor internals.
- Minimal API/payload shape: `{ deckId: number, noteTypeId?: number, fields: Record<string, string>, tags: string[] }`.
- Deterministic placeholder acceptable temporarily: yes. The UI keeps the lightweight composer visible and routes `Add card draft` to Add Cards for the selected deck without silently inserting fake cards.
- Blocked visual/interaction requirement: one-click creation of the exact visible prompt/answer draft from inside the Study workspace.

## CFA-topic deck creation preset

- Required capability: create a new deck from a CFA topic preset, optionally including default tags/note type.
- Why existing data is insufficient: Anki's existing deck creation dialog creates named decks, but it does not know about CFA topic presets or starter metadata.
- Minimal API/payload shape: `{ topic: string, deckName: string, parentDeckId?: number, defaultTags: string[], noteTypeId?: number }`.
- Deterministic placeholder acceptable temporarily: yes. Both `Create new deck` and `Create CFA deck` open the existing deck creation dialog.
- Blocked visual/interaction requirement: true one-step CFA-topic deck creation from the frozen Fast Create panel.
