// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { ExamReadinessPayload, TopicRow } from "../types";
import {
    bandValue,
    buildReadinessRisks,
    captionText,
    readinessLead,
    READINESS_NAV,
    retentionWatchlist,
    noRecallYet,
    topicRows,
} from "./readiness";

const here = dirname(fileURLToPath(import.meta.url));

function componentSource(): string {
    return readFileSync(join(here, "CfaReadinessPage.svelte"), "utf8");
}

function topic(over: Partial<TopicRow>): TopicRow {
    return {
        topic: "Equity Investments",
        weight: 0.12,
        reviewedCards: 0,
        gradedReviews: 0,
        recallRange: null,
        covered: true,
        ...over,
    };
}

function payload(over: Partial<ExamReadinessPayload> = {}): ExamReadinessPayload {
    return {
        deckName: "CFA Level II",
        heroMode: "bayesian_call",
        heroBayesian: {
            call: "Borderline positive",
            callProb: 0.66,
            passed: true,
            accuracy: 0.69,
            ciLow: 0.66,
            ciHigh: 0.72,
            mps: 0.65,
            recall: 0.71,
            firstExposures: 96,
            topicsCovered: 8,
            topicsTotal: 10,
            label: "Borderline",
        },
        memory: {
            name: "Memory",
            meaning: "Scheduled recall durability and predicted forgetting risk.",
            abstain: false,
            reason: "",
            point: 0.77,
            rangeLow: 0.74,
            rangeHigh: 0.8,
        },
        performance: {
            name: "Performance",
            meaning: "Graded vignettes and new-question execution under exam pressure.",
            abstain: false,
            reason: "",
            point: 0.64,
            rangeLow: 0.61,
            rangeHigh: 0.67,
        },
        readiness: {
            name: "Readiness",
            label: "Borderline",
            meaning: "Projected pass readiness range from coverage, memory, and graded evidence.",
            abstain: false,
            reason: "",
            point: 0.69,
            rangeLow: 0.66,
            rangeHigh: 0.72,
        },
        caption: {
            coveragePct: 0.82,
            topicsCovered: 8,
            topicsTotal: 10,
            gradedReviews: 1284,
            firstExposures: 96,
            lastReviewAt: "14:32",
        },
        topics: [],
        footerText: "Scores use existing CFA readiness data.",
        ...over,
    };
}

test("noRecallYet: true when every topic row has no recall data", () => {
    const rows = topicRows([
        topic({ topic: "Ethics & Professional Standards" }),
        topic({ topic: "Equity Investments" }),
    ]);
    expect(noRecallYet(rows)).toBe(true);
});

test("noRecallYet: false once any topic has a recall range", () => {
    const rows = topicRows([
        topic({ topic: "Ethics & Professional Standards" }),
        topic({ topic: "Equity Investments", recallRange: { low: 0.6, high: 0.7 } }),
    ]);
    expect(noRecallYet(rows)).toBe(false);
});

test("noRecallYet: false for an empty table (no rows to describe)", () => {
    expect(noRecallYet([])).toBe(false);
});

test("topicRows: sorts weightiest first, then by topic name (deterministic tiebreak)", () => {
    const rows = topicRows([
        topic({ topic: "Portfolio Management", weight: 0.12 }),
        topic({ topic: "Economics", weight: 0.09 }),
        topic({ topic: "Equity Investments", weight: 0.12 }),
    ]);
    expect(rows.map((r) => r.topic)).toStrictEqual([
        "Equity Investments",
        "Portfolio Management",
        "Economics",
    ]);
    expect(rows[0].weight).toBe("12%");
});

test("captionText: omits the unfinished 'as of —' clause when no timestamp", () => {
    const base = {
        coveragePct: 1,
        topicsCovered: 10,
        topicsTotal: 10,
        gradedReviews: 0,
        firstExposures: 0,
        lastReviewAt: null,
    };
    expect(captionText(base)).not.toContain("as of");
    expect(captionText({ ...base, lastReviewAt: "2026-07-04" })).toContain("as of 2026-07-04");
});

test("bandValue: preserves separate frozen score ranges and honest no-score state", () => {
    expect(bandValue(payload().memory)).toBe("74-80");
    expect(bandValue({ ...payload().memory, abstain: true, rangeLow: null, rangeHigh: null })).toBe("No score");
});

test("readinessLead: frames pass calls as local unvalidated evidence", () => {
    expect(readinessLead(payload())).toContain("66-72 projected readiness range");
    expect(readinessLead(payload())).toContain("not validated against real CFA exam data");
    expect(readinessLead(payload({ heroMode: "abstain", heroBayesian: undefined, heroAbstain: { reason: "Need more graded reviews", readinessLabel: "No call" } }))).toContain("No pass/fail call yet");
});

test("buildReadinessRisks: surfaces weak heavy topics before strong topics", () => {
    const risks = buildReadinessRisks([
        topic({ topic: "Ethics & Professional Standards", weight: 0.12, recallRange: { low: 0.81, high: 0.87 }, gradedReviews: 182 }),
        topic({ topic: "Financial Reporting & Analysis", weight: 0.12, recallRange: { low: 0.52, high: 0.64 }, gradedReviews: 88 }),
        topic({ topic: "Derivatives", weight: 0.05, recallRange: null, covered: false }),
    ]);
    expect(risks[0].title).toBe("FRA recall decay");
    expect(risks[0].label).toBe("Volatile");
    expect(risks.map((risk) => risk.topic)).toContain("Derivatives");
});

test("retentionWatchlist: stays honest when exact fading cards are not in payload", () => {
    const rows = retentionWatchlist([
        topic({ topic: "Derivatives", recallRange: null, covered: false, reviewedCards: 12 }),
    ]);
    expect(rows[0].title).toBe("Derivatives retention checkpoint");
    expect(rows[0].detail).toContain("exact fading cards need card-level backend evidence");
    expect(rows[0].risk).toBe("no card score");
});

test("Readiness page keeps frozen exam-risk console selectors", () => {
    const src = componentSource();
    expect(src).toContain("Readiness - Exam Risk Console");
    expect(src).toContain("Are you ready to pass?");
    expect(src).toContain('class="cfa-readiness__appbar"');
    expect(src).toContain('class="cfa-readiness__hero cfa-hero"');
    expect(src).toContain('class="cfa-readiness__score-card"');
    expect(src).toContain("cfa-readiness__console-grid");
    expect(src).toContain('class="cfa-readiness__retention-watch"');
    expect(src).toContain("No blended number.");
});

test("Readiness page routes top tabs and CTAs to existing bridge flows", () => {
    const src = componentSource();
    for (const cmd of READINESS_NAV.map((item) => item.cmd)) {
        expect(cmd).toMatch(/^cfa:/);
    }
    for (const cmd of ["cfa:risk-session", "cfa:readiness-drill", "cfa:mock-review", "cfa:retention-queue", "cfa:plan", "cfa:mock-schedule"]) {
        expect(src).toContain(cmd);
    }
});
