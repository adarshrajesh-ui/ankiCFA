# Readiness Backend Gaps

## Card-level forgetting watchlist

- Required capability: return the exact cards predicted to slip below the recall threshold, with topic, last clean recall, fade risk, and a launchable retention queue.
- Why existing data is insufficient: `getCfaExamReadiness` exposes score ranges, topic rows, evidence counts, and the hero call/abstain state, but it does not expose card IDs or per-card fade-risk rows for the frozen Forgetting Watchlist.
- Minimal API/payload shape: `{ cardId: number, topic: string, title: string, lastCleanRecallDays: number | null, fadeRisk: number, launchCommand: string }`.
- Temporary deterministic placeholder: acceptable. The UI shows a clearly labelled topic-level proxy derived from current recall ranges and routes `Pull retention queue` to the existing deadline-aware retention flow.
- Blocked visual/interaction requirement: exact "what I am about to forget" card list and one-click queue containing those precise cards.

## Mock exam review and scheduling

- Required capability: expose latest mock-exam attempt metadata and a mock planning/scheduling destination.
- Why existing data is insufficient: the current Readiness payload has graded review evidence and local pass/readiness bands, but no mock-attempt object, timestamp, section scores, or scheduler state.
- Minimal API/payload shape: `{ latestMockId?: string, completedAt?: string, scoreRange?: { low: number, high: number }, reviewCommand?: string, scheduleCommand?: string }`.
- Temporary deterministic placeholder: acceptable. The UI keeps the frozen actions visible and delegates both mock buttons to the existing deadline/readiness planning flow.
- Blocked visual/interaction requirement: opening a specific latest mock review or scheduling a full mock from this screen.
