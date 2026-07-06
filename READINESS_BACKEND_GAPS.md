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
- Temporary deterministic placeholder: none. The UI disables the latest mock review action with explicit unavailable copy and no longer shows a `Schedule full mock` CTA until a real mock destination exists.
- Blocked visual/interaction requirement: opening a specific latest mock review or scheduling a full mock from this screen.

## Composed 35-minute and per-topic risk-drill queues

- Required capability: return a launchable readiness plan with topic-scoped drill queues, ordered card IDs, time budgets, and a bridge command for each drill.
- Why existing data is insufficient: `getCfaExamReadiness` can rank topic risk and evidence, but it does not expose topic-filtered queue IDs or a composed plan object that the reviewer can launch directly.
- Minimal API/payload shape: `{ title: string, topic: string, cardIds: number[], estimatedMinutes: number, launchCommand: string }[]`.
- Temporary deterministic placeholder: the UI shows topic-level recommendations and routes their action to the existing weakest-first exam-priority study flow (`cfa:risk-session`). It no longer shows the unsupported `Begin 35-minute plan` CTA.
- Blocked visual/interaction requirement: one-click launch of an exact 35-minute composed plan or exact per-topic risk drill from Readiness.
