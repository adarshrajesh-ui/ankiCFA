// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// CFA web design-system data contracts.
//
// These payload types are the shape the page agents (Exam Readiness, Deadline)
// build from the Rust/Python backend and hand to the shared components. They
// mirror the honest-score model produced by the desktop surfaces
// (qt/aqt/cfa.py, pylib CFA scores) so the web pages present the SAME data.
// -----------------------------------------------------------------------------

/** A low/high recall band for a single topic. */
export interface RecallRange {
    low: number;
    high: number;
}

/**
 * One honest score presented as a labelled range with an explicit "abstain"
 * (not-enough-data) rule. `point` is the best single estimate; `rangeLow` /
 * `rangeHigh` bound it. When `abstain` is true the score is withheld and
 * `reason` explains why.
 */
export interface ScoreBand {
    name: string;
    meaning: string;
    abstain: boolean;
    reason: string;
    point: number | null;
    rangeLow: number | null;
    rangeHigh: number | null;
}

/** The readiness band additionally carries a human-readable verdict label. */
export type ReadinessBand = ScoreBand & { label: string };

/**
 * The Bayesian pass/fail verdict (F4): an explicit call with a probability, a
 * 95% credible accuracy band, the minimum passing standard (mps) and coverage.
 */
export interface HeroBayesian {
    call: string;
    callProb: number;
    passed: boolean;
    accuracy: number;
    ciLow: number;
    ciHigh: number;
    mps: number;
    recall: number | null;
    firstExposures: number;
    topicsCovered: number;
    topicsTotal: number;
    label: string;
}

/** The "not enough data yet" hero state — no call is made. */
export interface HeroAbstain {
    reason: string;
    readinessLabel: string;
}

/** The quiet footnote summarising coverage + review provenance. */
export interface ExamReadinessCaption {
    coveragePct: number;
    topicsCovered: number;
    topicsTotal: number;
    gradedReviews: number;
    firstExposures: number;
    lastReviewAt: string | null;
}

/** One row of the per-topic recall table. */
export interface TopicRow {
    topic: string;
    weight: number;
    reviewedCards: number;
    gradedReviews: number;
    recallRange: RecallRange | null;
    covered: boolean;
}

/** Full payload for the Exam Readiness page. */
export interface ExamReadinessPayload {
    deckName: string;
    heroMode: "abstain" | "bayesian_call";
    heroBayesian?: HeroBayesian;
    heroAbstain?: HeroAbstain;
    memory: ScoreBand;
    performance: ScoreBand;
    readiness: ReadinessBand;
    caption: ExamReadinessCaption;
    topics: TopicRow[];
    footerText: string;
}

/**
 * Full payload for the CFA Home dashboard — the native landing screen. It
 * carries the SAME three honest scores + Bayesian hero as Exam Readiness (built
 * by reusing that payload for score parity), plus the exam countdown and the
 * master AI-toggle state for the dashboard chrome.
 */
export interface CfaHomePayload extends ExamReadinessPayload {
    /** ISO date string of the configured exam, or null if not set yet. */
    examDate: string | null;
    /** Whole days until the exam (0 == today), or null if no exam date set. */
    daysToExam: number | null;
    /** Master AI toggle (col.conf `cfa_ai_enabled`); default OFF. */
    aiEnabled: boolean;
    /** CFA sync/account status for the in-app Settings & Sync card. */
    sync: {
        connected: boolean;
        syncing: boolean;
        status: string;
        tone: CfaTone;
        account: string;
        lastSyncedAt: string | null;
        lastSyncedLabel: string;
        endpoint: string;
        detail: string;
        actionLabel: string;
    };
}

/** One deck card shown in the frozen Study workspace. */
export interface CfaStudyDeck {
    id: number;
    name: string;
    description: string;
    due: number;
    newCount: number;
    learn: number;
    review: number;
    mastery: number | null;
    featured: boolean;
}

/** Full payload for the deck-first CFA Study page. */
export interface CfaStudyPayload {
    sync: CfaHomePayload["sync"];
    totals: {
        activeDecks: number;
        dueToday: number;
        newQueued: number;
    };
    decks: CfaStudyDeck[];
    selectedDeckId: number | null;
    footerText: string;
}

/** One ranked row of the Deadline planner table. */
export interface DeadlineRow {
    cardId: number;
    predictedRecall: number;
    suggestedIntervalDays: number;
    warnLowRecall: boolean;
    /**
     * True for a never-studied (NEW) card. Such a card has no FSRS memory state,
     * so its predicted exam-day recall is 0.0 by construction — not a genuine
     * "you will forget everything" figure. The page renders these calmly as
     * "New" (not an alarming warn-orange "0.0%").
     */
    isNew: boolean;
}

/** Full payload for the Deadline planner page. */
export interface DeadlinePayload {
    examDate: string;
    topicWeights: Record<string, number>;
    cardCount: number;
    dataSource: "Rust RPC" | "read-only fallback";
    headerMode: "empty" | "ranked";
    rows: DeadlineRow[];
    footerText: string;
}

// -----------------------------------------------------------------------------
// Component-level helper types.
// -----------------------------------------------------------------------------

/**
 * Semantic tone shared across components (never washes out the pass/fail triad).
 * `muted` is the QUIET neutral used for honest "no data yet" states — it must
 * read as calm absence, never as a warning (reserve `warn` for real cautions).
 */
export type CfaTone = "neutral" | "pass" | "fail" | "warn" | "muted";

/** A column definition for the shared `DataTable`. */
export interface CfaColumn {
    /** Key into each row object. */
    key: string;
    /** Uppercased-by-CSS header label. */
    label: string;
    /** Alignment; numeric columns should be `"right"`. */
    align?: "left" | "right";
    /** Optional fixed/max width (any CSS length). */
    width?: string;
}

/** A generic row for the shared `DataTable` (keyed by column `key`). */
export type CfaRow = Record<string, unknown>;
