// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Pure display helpers for the Deadline planner page. Kept out of the Svelte
// component so the new-card / at-risk presentation logic is trivially testable
// (no DOM, no Svelte). A never-studied (NEW) card has no FSRS memory state, so
// its predicted exam-day recall is 0.0 by construction — these helpers render it
// as a calm "New" rather than an alarming warn-orange "0.0%".
// -----------------------------------------------------------------------------

import type { DeadlineRow } from "../types";

/** The recall cell text: a whole-first-decimal percent for studied cards, or a
 * calm "New" for a never-studied card (whose 0.0 is a placeholder, not a fact). */
export function recallCell(row: DeadlineRow): string {
    return row.isNew ? "New" : `${(row.predictedRecall * 100).toFixed(1)}%`;
}

/** The capped-interval cell text: a plain integer for studied cards, or an
 * em-free en-dash for a new card (no schedule yet). */
export function intervalCell(row: DeadlineRow): string {
    return row.isNew ? "–" : String(row.suggestedIntervalDays);
}

/** Whether a row is a studied card whose predicted exam-day recall has fallen
 * below the 0.85 at-risk threshold. A never-studied NEW card is NEVER "at risk" —
 * it has no memory model yet, so its 0.0 is a placeholder, not a real recall. */
export function isAtRisk(row: DeadlineRow): boolean {
    return row.warnLowRecall && !row.isNew;
}

/**
 * A non-colour (shape) marker prefixed to an at-risk recall figure so the
 * at-risk state is perceivable WITHOUT relying on the warn-orange colour alone
 * (WCAG 2.1 SC 1.4.1 Use of Color — ~8% of men have a red-green colour vision
 * deficiency and cannot see orange-vs-ink). A solid up-triangle reads as
 * "attention" by shape; empty for healthy or new rows.
 */
export function riskMarker(row: DeadlineRow): string {
    return isAtRisk(row) ? "▲" : "";
}

/** The screen-reader / non-visual label for an at-risk row (redundant with the
 * shape marker + colour so the state never depends on a single channel). */
export const RISK_LABEL = "at risk";

/** How many of the ranked rows are never-studied new cards. */
export function newCardCount(rows: DeadlineRow[]): number {
    return rows.filter((r) => r.isNew).length;
}

/** True when every ranked row is a new card (a fresh, unstudied deck) — the
 * degenerate all-"0.0%" case that must not read as a wall of alarming zeros. */
export function allNew(rows: DeadlineRow[]): boolean {
    return rows.length > 0 && rows.every((r) => r.isNew);
}

/** A calm hint shown above the table when new cards are present, so the reader
 * understands why some rows read "New" instead of a recall figure. Returns "" when
 * there are no new cards (studied-only decks need no explanation). */
export function newCardHint(rows: DeadlineRow[]): string {
    const n = newCardCount(rows);
    if (n === 0) {
        return "";
    }
    if (allNew(rows)) {
        return "Every card here is new — a predicted exam-day recall appears for "
            + "each once you've studied it. New cards rank first: study them to "
            + "start building memory before the exam.";
    }
    const cardWord = n === 1 ? "card is" : "cards are";
    return `${n} new ${cardWord} shown first (no recall figure until studied); the `
        + "rest are ranked weakest exam-day recall first.";
}
