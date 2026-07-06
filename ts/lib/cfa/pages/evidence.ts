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
        return `No score: high-weight topics skipped: ${skipped[1]}`;
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
