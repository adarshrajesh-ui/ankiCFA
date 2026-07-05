# Concept Map Backend Gaps

## Per-subsection mastery evidence

- Required capability: return mastery, evidence count, and abstain status per CFA subsection.
- Why existing data is insufficient: `getCfaHomeView` exposes topic-level `TopicRow` evidence only. Orbit 2 can be drawn from the frozen hierarchy, but its mastery currently inherits the parent section estimate.
- Minimal API/payload shape: `{ id: string, parentTopic: string, name: string, mastery: number | null, gradedReviews: number, reviewedCards: number, covered: boolean }`.
- Temporary deterministic placeholder: acceptable. The UI labels subsection explanations as inherited section evidence and keeps insufficient evidence gray.
- Blocked visual/interaction requirement: independently colored orbit-2 subsection fills.

## Concept-specific fastest drill queue

- Required capability: launch or describe a study queue scoped to the pinned topic/subsection node, including due/new counts when available.
- Why existing data is insufficient: existing desktop flows support global CFA priority study and specific legacy entry points, but not a concept-id/subsection queue from the Concept Map.
- Minimal API/payload shape: `{ nodeId: string, topic: string, subsection?: string, dueCount: number, newCount: number, launchCommand: string, search?: string }`.
- Temporary deterministic placeholder: acceptable. The UI shows deterministic next-drill copy and routes the button to the existing `cfa:priority` flow without fake counts.
- Blocked visual/interaction requirement: exact per-node fastest drill and due-count preview.
