// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import type { ExamReadinessCaption, ScoreBand } from "../types";

export const MIN_GRADED_REVIEWS = 200;
export const MIN_TOPIC_COVERAGE = 0.5;
export const MIN_FIRST_EXPOSURES = 30;

type EvidenceGate = "gradedReviews" | "topicCoverage" | "firstExposures";

function integer(n: number): string {
    return n.toLocaleString("en-US");
}

function pct(x: number): string {
    return `${Math.round(x * 100)}%`;
}

function stripTrailingPunctuation(text: string): string {
    return text.trim().replace(/[.]+$/, "");
}

/**
 * Human-readable CFA topic-area names, keyed by the bare `los::<slug>` slug.
 * Mirrors `topic_display_name` in `pylib/anki/cfa.py` so the frontend can act as
 * a defensive safety net: even if a raw `los::` tag slips through in a backend
 * reason string, the skipped-topics list still renders readable area names.
 */
const TOPIC_DISPLAY_NAMES: Record<string, string> = {
    ethics: "Ethics & Professional Standards",
    quant: "Quantitative Methods",
    econ: "Economics",
    fra: "Financial Reporting & Analysis",
    corp: "Corporate Issuers",
    equity: "Equity Investments",
    "fixed-income": "Fixed Income",
    fixed_income: "Fixed Income",
    fi: "Fixed Income",
    derivatives: "Derivatives",
    altinv: "Alternative Investments",
    portmgmt: "Portfolio Management",
};

/**
 * Map a single topic token to a readable CFA area name: strip an optional
 * `los::` prefix, keep the segment before any further `::`, lowercase it, then
 * look it up. Unknown slugs fall back to a title-cased form (split on `_`/`-`)
 * so a newly-authored topic is still readable. An already-human name round-trips
 * unchanged. Returns the original token when there is nothing left to map.
 */
function topicDisplayName(token: string): string {
    const trimmed = token.trim();
    const bare = trimmed.startsWith("los::") ? trimmed.slice("los::".length) : trimmed;
    const slug = bare.split("::", 1)[0].trim().toLowerCase();
    if (!slug) {
        return trimmed;
    }
    if (slug in TOPIC_DISPLAY_NAMES) {
        return TOPIC_DISPLAY_NAMES[slug];
    }
    const words = slug.replace(/[_-]+/g, " ").split(/\s+/).filter(Boolean);
    return words.length
        ? words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ")
        : trimmed;
}

function cleanRawReason(reason: string): string {
    const trimmed = stripTrailingPunctuation(reason);
    if (!trimmed) {
        return "Not enough evidence yet";
    }
    if (/no topics found/i.test(trimmed)) {
        return "Not enough data: no CFA topics found";
    }
    const skipped = trimmed.match(/high-weight topic\(s\) skipped, no score:\s*(.+)$/i);
    if (skipped?.[1]) {
        const names = skipped[1]
            .split(",")
            .map((token) => topicDisplayName(token))
            .filter((name) => name.length > 0)
            .join(", ");
        return `No score: high-weight topics skipped: ${names}`;
    }
    return trimmed
        .replace(/^not enough data to estimate readiness:\s*/i, "Not enough data: ")
        .replace(/^not enough data:\s*/i, "Not enough data: ")
        .replace(/first-seen questions/gi, "first exposures");
}

function gateListForBand(band: ScoreBand): EvidenceGate[] {
    const name = band.name.toLowerCase();
    if (name.includes("performance")) {
        return ["firstExposures"];
    }
    if (name.includes("readiness")) {
        return ["gradedReviews", "topicCoverage", "firstExposures"];
    }
    return ["gradedReviews", "topicCoverage"];
}

function gateListFromReason(reason: string): EvidenceGate[] {
    const lower = reason.toLowerCase();
    if (lower.includes("first-seen") || lower.includes("first exposure")) {
        return ["firstExposures"];
    }
    if (lower.includes("memory") || lower.includes("performance")) {
        return ["gradedReviews", "topicCoverage", "firstExposures"];
    }
    return ["gradedReviews", "topicCoverage"];
}

function failedGateCopy(caption: ExamReadinessCaption, gates: EvidenceGate[]): string[] {
    const copy: string[] = [];
    if (gates.includes("gradedReviews") && caption.gradedReviews < MIN_GRADED_REVIEWS) {
        copy.push(`${integer(caption.gradedReviews)} graded reviews (need ${MIN_GRADED_REVIEWS})`);
    }
    if (gates.includes("topicCoverage") && caption.coveragePct < MIN_TOPIC_COVERAGE) {
        copy.push(`${pct(caption.coveragePct)} topic coverage (need ${pct(MIN_TOPIC_COVERAGE)})`);
    }
    if (gates.includes("firstExposures") && caption.firstExposures < MIN_FIRST_EXPOSURES) {
        copy.push(`${integer(caption.firstExposures)} first exposures (need ${MIN_FIRST_EXPOSURES})`);
    }
    return copy;
}

function rawReasonLooksLikeEvidenceGate(reason: string): boolean {
    return /graded reviews \(need|topic coverage \(need|first-seen questions \(need|first exposures \(need/i.test(
        reason,
    );
}

export function formatAbstainReasonForBand(band: ScoreBand, caption: ExamReadinessCaption): string {
    const failed = failedGateCopy(caption, gateListForBand(band));
    if (failed.length) {
        return `Not enough data: ${failed.join("; ")}`;
    }
    if (rawReasonLooksLikeEvidenceGate(band.reason)) {
        return "Not enough evidence yet";
    }
    return cleanRawReason(band.reason);
}

export function formatHeroAbstainReason(reason: string, caption: ExamReadinessCaption): string {
    const failed = failedGateCopy(caption, gateListFromReason(reason));
    if (failed.length) {
        return `Not enough data: ${failed.join("; ")}`;
    }
    if (rawReasonLooksLikeEvidenceGate(reason)) {
        return "Not enough evidence yet";
    }
    return cleanRawReason(reason);
}
