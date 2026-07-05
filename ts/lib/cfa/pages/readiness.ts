// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Pure formatting helpers for the Exam Readiness page. Kept out of the Svelte
// component so the number/percent/range formatting mirrors the desktop surface
// (qt/aqt/cfa.py `_pct`, `_band_html`, the per-topic table) exactly and stays
// trivially testable. No DOM, no Svelte — just data → display strings + tones.
// -----------------------------------------------------------------------------

import type { CfaColumn, CfaTone, ExamReadinessCaption, ReadinessBand, ScoreBand, TopicRow } from "../types";

/**
 * A recall high/mid below this reads as "at risk" and is warn-coloured in the
 * per-topic table. A rough CFA minimum-passing-standard proxy (~65%), nudged
 * down so only genuinely weak topics light up.
 */
export const LOW_RECALL = 0.6;

/** Format a 0..1 fraction as a whole-percent string, mirroring `_pct`. */
export function pct(x: number | null | undefined): string {
    return x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`;
}

/** A low–high range as `68%–74%` (em-free en-dash, like the desktop). */
export function rangeText(low: number | null, high: number | null): string {
    return `${pct(low)}–${pct(high)}`;
}

/**
 * The big serif value for an honest-score StatCard: the range when scored, or a
 * SHORT, calm placeholder while abstaining. The full "not enough data" verdict
 * is stated once in the hero — the cards stay quiet ("Awaiting reviews") with the
 * give-up reason in the sub-line, so the empty state never shouts three times.
 */
export function bandValue(band: ScoreBand): string {
    return band.abstain ? "Awaiting reviews" : rangeText(band.rangeLow, band.rangeHigh);
}

/**
 * StatCard value tone. Abstain is `muted` (quiet faint grey) — an honest ABSENCE
 * of data, deliberately NOT `warn`-orange, so it does not read as a warning nor
 * collide with the warm primary-CTA hue (color-semantic separation).
 */
export function bandTone(band: ScoreBand): CfaTone {
    return band.abstain ? "muted" : "neutral";
}

/** The faint sub-line under a StatCard: the give-up reason, or the midpoint. */
export function bandSub(band: ScoreBand): string {
    return band.abstain ? band.reason : `midpoint ${pct(band.point)}`;
}

/** The readiness card carries its verdict label alongside the name. */
export function readinessName(band: ReadinessBand): string {
    return band.label ? `${band.name} — ${band.label}` : band.name;
}

/** The per-topic recall cell text: a range, or an explicit "no data". */
export function recallText(row: TopicRow): string {
    return row.recallRange === null
        ? "no data"
        : rangeText(row.recallRange.low, row.recallRange.high);
}

/**
 * Recall cell tone: quiet muted for no-data, warn for uncovered or low recall,
 * neutral otherwise. Never washes out the semantic triad.
 */
export function recallTone(row: TopicRow): "neutral" | "warn" | "muted" {
    if (row.recallRange === null) {
        return "muted";
    }
    if (!row.covered || row.recallRange.high < LOW_RECALL) {
        return "warn";
    }
    return "neutral";
}

/** One display row for the shared DataTable (all cells pre-formatted). */
export interface TopicDisplayRow {
    topic: string;
    weight: string;
    reviewed: number;
    graded: number;
    recall: string;
    recallTone: "neutral" | "warn" | "muted";
    [key: string]: unknown;
}

/** The five UPPERCASE, right-aligned-numeric columns of the recall table. */
export const TOPIC_COLUMNS: CfaColumn[] = [
    { key: "topic", label: "Topic", align: "left" },
    { key: "weight", label: "Weight", align: "right" },
    { key: "reviewed", label: "Reviewed", align: "right" },
    { key: "graded", label: "Graded", align: "right" },
    { key: "recall", label: "Recall R (range)", align: "right" },
];

/**
 * Build the recall-table rows, weightiest topic first (like the desktop), with
 * a deterministic secondary sort by topic name so equal-weight areas always
 * appear in the same, scannable order rather than an arbitrary tiebreak.
 */
export function topicRows(topics: TopicRow[]): TopicDisplayRow[] {
    return [...topics]
        .sort((a, b) => b.weight - a.weight || a.topic.localeCompare(b.topic))
        .map((t) => ({
            topic: t.topic,
            weight: t.weight.toFixed(2),
            reviewed: t.reviewedCards,
            graded: t.gradedReviews,
            recall: recallText(t),
            recallTone: recallTone(t),
        }));
}

/**
 * True when the coverage table has topic rows but none has any recall data yet
 * (every recall cell reads "no data"). Used to show a SINGLE calm hint line
 * above the table on a fresh deck rather than leaving ten visually flat,
 * identical "no data" rows with no explanation (D2-5).
 */
export function noRecallYet(rows: TopicDisplayRow[]): boolean {
    return rows.length > 0 && rows.every((r) => r.recall === "no data");
}

/** The quiet coverage/graded/first-exposure caption line. The "as of …" clause
 * is omitted entirely until there is a real last-review timestamp, so a fresh
 * deck never shows an unfinished-looking "as of —" placeholder. */
export function captionText(c: ExamReadinessCaption): string {
    const base = `Coverage ${pct(c.coveragePct)} (${c.topicsCovered}/${c.topicsTotal} topics) · `
        + `${c.gradedReviews} graded reviews · ${c.firstExposures} first-seen`;
    return c.lastReviewAt ? `${base} · as of ${c.lastReviewAt}` : base;
}
