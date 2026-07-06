// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Pure formatting helpers for the Readiness "Exam Risk Console". The Svelte page
// owns the glass layout; this module keeps all score/risk/watchlist derivation
// deterministic and testable, using only the existing honest-readiness payload.
// -----------------------------------------------------------------------------

import { productNavItems } from "../productNav";
import type {
    CfaColumn,
    CfaTone,
    ExamReadinessCaption,
    ExamReadinessPayload,
    ReadinessBand,
    ScoreBand,
    TopicRow,
} from "../types";

import { formatAbstainReasonForBand, formatHeroAbstainReason } from "./evidence";
import { shortTopicName } from "./home";

/**
 * A recall high/mid below this reads as "at risk" and is warn-coloured in the
 * per-topic table. A rough CFA minimum-passing-standard proxy (~65%), nudged
 * down so only genuinely weak topics light up.
 */
export const LOW_RECALL = 0.6;

export const READINESS_NAV = productNavItems("readiness");

export interface ReadinessScoreCard {
    name: string;
    meaning: string;
    band: ScoreBand;
}

/** Format an integer with the user's locale grouping used by the frozen cards. */
export function integer(n: number): string {
    return n.toLocaleString("en-US");
}

/** Format a 0..1 fraction as a whole-percent string, mirroring `_pct`. */
export function pct(x: number | null | undefined): string {
    return x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`;
}

/** A low–high range as `68%–74%` (em-free en-dash, like the desktop). */
export function rangeText(low: number | null, high: number | null): string {
    return `${pct(low)}–${pct(high)}`;
}

/**
 * The frozen score cards show whole-number ranges without percent signs:
 * Memory 74-80, Performance 61-67, Readiness 66-72. Abstain stays explicit.
 */
export function bandValue(band: ScoreBand): string {
    if (band.abstain || band.rangeLow === null || band.rangeHigh === null) {
        return "No score";
    }
    return `${Math.round(band.rangeLow * 100)}-${Math.round(band.rangeHigh * 100)}`;
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
export function bandSub(band: ScoreBand, caption: ExamReadinessCaption): string {
    return band.abstain ? formatAbstainReasonForBand(band, caption) : `midpoint ${pct(band.point)}`;
}

/** The readiness card carries its verdict label alongside the name. */
export function readinessName(band: ReadinessBand): string {
    return band.label ? `${band.name} — ${band.label}` : band.name;
}

export function readinessScoreCards(data: ExamReadinessPayload): ReadinessScoreCard[] {
    return [
        { name: data.memory.name, meaning: data.memory.meaning, band: data.memory },
        { name: data.performance.name, meaning: data.performance.meaning, band: data.performance },
        { name: data.readiness.name, meaning: data.readiness.meaning, band: data.readiness },
    ];
}

export function syncChipLabel(data: ExamReadinessPayload): string {
    if (data.caption.lastReviewAt) {
        return `Readiness updated ${data.caption.lastReviewAt}`;
    }
    return data.heroMode === "abstain" ? "Readiness awaiting evidence" : "Readiness updated locally";
}

export function readinessLead(data: ExamReadinessPayload): string {
    if (data.heroMode === "bayesian_call" && data.heroBayesian) {
        const scoreRange = bandValue(data.readiness);
        return `Pass call: ${data.heroBayesian.call.toLowerCase()}, ${scoreRange} estimated exam accuracy as a 95% confidence interval. Based on stored reviews, first exposures, graded answers, and topic coverage; the range narrows as you answer more questions, and Readiness withholds the call when evidence is thin.`;
    }
    if (data.heroAbstain) {
        const reason = formatHeroAbstainReason(data.heroAbstain.reason, data.caption);
        return `No pass/fail call yet: ${reason}. Keep studying to build enough review, first-exposure, and coverage evidence.`;
    }
    return "No pass/fail call yet. Readiness withholds the call until enough review, first-exposure, and coverage evidence is available.";
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
    reviewedGraded: string;
    recall: string;
    recallTone: "neutral" | "warn" | "muted";
    covered: boolean;
    sub: string;
    barWidth: number;
    barTone: "neutral" | "warn" | "danger";
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
            weight: pct(t.weight),
            reviewed: t.reviewedCards,
            graded: t.gradedReviews,
            reviewedGraded: `${pct(reviewedCoverage(t))} / ${integer(t.gradedReviews)}`,
            recall: recallText(t),
            recallTone: recallTone(t),
            covered: t.covered,
            sub: topicSub(t),
            barWidth: recallBarWidth(t),
            barTone: recallBarTone(t),
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

export interface ReadinessRisk {
    topic: string;
    title: string;
    detail: string;
    label: string;
    tone: "high" | "med" | "keep";
    priority: number;
}

export interface RetentionItem {
    title: string;
    detail: string;
    risk: string;
}

export interface ActionPlanItem {
    title: string;
    detail: string;
    time: string;
    cmd: string;
    cta: string;
    routeNote: string;
    ariaLabel: string;
}

function midpoint(row: TopicRow): number | null {
    return row.recallRange === null ? null : (row.recallRange.low + row.recallRange.high) / 2;
}

function reviewedCoverage(row: TopicRow): number {
    if (!row.covered) {
        return 0;
    }
    const evidence = row.reviewedCards + row.gradedReviews;
    return Math.max(0.03, Math.min(0.99, evidence / 220));
}

function topicSub(row: TopicRow): string {
    if (!row.covered || row.recallRange === null) {
        return "Evidence gap flagged";
    }
    if (row.recallRange.high < LOW_RECALL) {
        return "High-weight gap flagged";
    }
    if (row.recallRange.low < 0.65) {
        return "Near threshold";
    }
    return "Stable pass buffer";
}

function recallBarWidth(row: TopicRow): number {
    if (row.recallRange === null) {
        return row.covered ? 12 : 7;
    }
    return Math.max(8, Math.min(100, Math.round(row.recallRange.high * 100)));
}

function recallBarTone(row: TopicRow): "neutral" | "warn" | "danger" {
    if (!row.covered || row.recallRange === null || row.recallRange.high < LOW_RECALL) {
        return "danger";
    }
    if (row.recallRange.low < 0.65) {
        return "warn";
    }
    return "neutral";
}

function riskPriority(row: TopicRow): number {
    const m = midpoint(row);
    const weakness = m === null ? 0.72 : 1 - m;
    const coveragePenalty = row.covered ? 0 : 0.16;
    return row.weight * (weakness + coveragePenalty);
}

function riskLabel(row: TopicRow): Pick<ReadinessRisk, "label" | "tone"> {
    if (!row.covered || row.recallRange === null || row.recallRange.high < LOW_RECALL) {
        return { label: "High risk", tone: "high" };
    }
    if (row.recallRange.low < 0.68) {
        return { label: "Volatile", tone: "med" };
    }
    return { label: "Maintain", tone: "keep" };
}

function riskTitle(row: TopicRow): string {
    const short = shortTopicName(row.topic);
    if (short === "FRA") {
        return "FRA recall decay";
    }
    if (short === "Ethics") {
        return "Ethics accuracy volatility";
    }
    if (short === "Quant") {
        return "Quant formulas under timed pressure";
    }
    return `${short} pass buffer risk`;
}

export function buildReadinessRisks(topics: TopicRow[], limit = 3): ReadinessRisk[] {
    return [...topics]
        .map((topic) => {
            const label = riskLabel(topic);
            const priority = riskPriority(topic);
            return {
                topic: topic.topic,
                title: riskTitle(topic),
                detail: `${shortTopicName(topic.topic)} carries ${pct(topic.weight)} exam weight with ${
                    integer(topic.reviewedCards)
                } reviewed cards, ${integer(topic.gradedReviews)} graded reviews, and ${
                    recallText(topic)
                } recall evidence.`,
                priority,
                ...label,
            };
        })
        .sort((a, b) => b.priority - a.priority || a.topic.localeCompare(b.topic))
        .slice(0, limit);
}

export function confidenceChips(topics: TopicRow[]): { label: string; tone: "turq" | "warn" | "neutral" }[] {
    const strong = [...topics]
        .filter((topic) => topic.recallRange !== null && topic.recallRange.low >= 0.72)
        .sort((a, b) => (b.recallRange?.low ?? 0) - (a.recallRange?.low ?? 0))
        .slice(0, 2)
        .map((topic) => shortTopicName(topic.topic));
    const uncovered = [...topics]
        .filter((topic) => !topic.covered || topic.recallRange === null)
        .sort((a, b) => b.weight - a.weight || a.topic.localeCompare(b.topic))
        .slice(0, 2)
        .map((topic) => shortTopicName(topic.topic));

    return [
        { label: strong.length ? `Strong: ${strong.join(", ")}` : "Strong: awaiting evidence", tone: "turq" },
        { label: uncovered.length ? `Uncovered: ${uncovered.join(", ")}` : "Uncovered: none flagged", tone: "warn" },
        { label: "Evidence: stored reviews", tone: "neutral" },
    ];
}

export function retentionWatchlist(topics: TopicRow[], limit = 3): RetentionItem[] {
    return [...topics]
        .sort((a, b) => riskPriority(b) - riskPriority(a) || a.topic.localeCompare(b.topic))
        .slice(0, limit)
        .map((topic) => {
            const low = topic.recallRange?.low ?? null;
            const risk = low === null ? "no card score" : `${Math.round((1 - low) * 100)}% fade risk`;
            return {
                title: `${shortTopicName(topic.topic)} retention checkpoint`,
                detail: topic.recallRange === null
                    ? `${integer(topic.reviewedCards)} reviewed cards - recall range appears after more graded evidence`
                    : `${rangeText(topic.recallRange.low, topic.recallRange.high)} recall - ${
                        integer(topic.gradedReviews)
                    } graded reviews`,
                risk,
            };
        });
}

export function actionPlan(risks: ReadinessRisk[]): ActionPlanItem[] {
    const plan = risks.length ? risks : [
        {
            topic: "CFA",
            title: "Build readiness evidence",
            detail: "Start with priority study until enough evidence unlocks the pass/fail call.",
            label: "High risk",
            tone: "high",
            priority: 0,
        } satisfies ReadinessRisk,
    ];
    const times = ["18 min", "7 min", "10 min"];
    return plan.slice(0, 3).map((risk, index) => {
        const topic = shortTopicName(risk.topic);
        return {
            title: `${topic} priority focus`,
            detail: risk.detail,
            time: times[index] ?? "10 min",
            cmd: "cfa:risk-session",
            cta: "Start priority study",
            routeNote: "Uses the existing weakest-first priority study flow.",
            ariaLabel: `Start priority study for ${topic}`,
        };
    });
}
