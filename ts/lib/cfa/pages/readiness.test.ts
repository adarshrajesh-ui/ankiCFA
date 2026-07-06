// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";

import type { ExamReadinessPayload, TopicRow } from "../types";
import {
    actionPlan,
    bandSub,
    bandValue,
    buildReadinessRisks,
    captionText,
    confidenceChips,
    noRecallYet,
    READINESS_NAV,
    readinessLead,
    retentionWatchlist,
    topicRows,
} from "./readiness";

const here = dirname(fileURLToPath(import.meta.url));

function componentSource(): string {
    return readFileSync(join(here, "CfaReadinessPage.svelte"), "utf8");
}

function productNavSource(): string {
    return readFileSync(join(here, "../ProductShellNav.svelte"), "utf8");
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
    expect(bandValue(payload().performance)).toBe("61-67");
    expect(bandValue(payload().readiness)).toBe("66-72");
    expect(bandValue({ ...payload().memory, abstain: true, rangeLow: null, rangeHigh: null })).toBe("No score");
});

test("bandSub: abstain reasons name only actually failed evidence gates", () => {
    const data = payload({
        memory: {
            ...payload().memory,
            abstain: true,
            reason: "not enough data: 1159 graded reviews (need 200), 42% topic coverage (need 50%)",
            point: null,
            rangeLow: null,
            rangeHigh: null,
        },
        caption: {
            ...payload().caption,
            coveragePct: 0.42,
            topicsCovered: 4,
            gradedReviews: 1159,
        },
    });

    expect(bandSub(data.memory, data.caption)).toBe("Not enough data: 42% topic coverage (need 50%)");
    expect(bandSub(data.memory, data.caption)).not.toContain("graded reviews (need 200)");
});

test("readinessLead: uses product copy without implementation-gap language", () => {
    expect(readinessLead(payload())).toContain("66-72 estimated exam accuracy as a 95% confidence interval");
    expect(readinessLead(payload())).not.toMatch(/Bayesian|backend|FSRS|no-AI|not validated|local evidence model/i);
    expect(readinessLead(payload({
        heroMode: "abstain",
        heroBayesian: undefined,
        heroAbstain: {
            reason: "not enough data: 1159 graded reviews (need 200), 42% topic coverage (need 50%)",
            readinessLabel: "No call",
        },
        caption: {
            ...payload().caption,
            coveragePct: 0.42,
            topicsCovered: 4,
            gradedReviews: 1159,
        },
    }))).toContain("No pass/fail call yet: Not enough data: 42% topic coverage (need 50%)");
});

test("buildReadinessRisks: surfaces weak heavy topics before strong topics", () => {
    const risks = buildReadinessRisks([
        topic({
            topic: "Ethics & Professional Standards",
            weight: 0.12,
            recallRange: { low: 0.81, high: 0.87 },
            gradedReviews: 182,
        }),
        topic({
            topic: "Financial Reporting & Analysis",
            weight: 0.12,
            recallRange: { low: 0.52, high: 0.64 },
            gradedReviews: 88,
        }),
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
    expect(rows[0].detail).toContain("recall range appears after more graded evidence");
    expect(rows[0].detail).not.toMatch(/backend|exact fading cards/i);
    expect(rows[0].risk).toBe("no card score");
});

test("actionPlan: routes risk recommendations to existing priority study", () => {
    const plan = actionPlan(buildReadinessRisks([
        topic({ topic: "Financial Reporting & Analysis", weight: 0.15, recallRange: { low: 0.42, high: 0.58 } }),
    ]));
    expect(plan[0].title).toBe("FRA priority focus");
    expect(plan[0].cmd).toBe("cfa:risk-session");
    expect(plan[0].cta).toBe("Start priority study");
    expect(plan[0].routeNote).toMatch(/existing weakest-first priority study/);
    expect(plan[0].title).not.toContain("risk drill");
});

test("confidenceChips: avoids no-AI explanatory copy in Readiness UI", () => {
    expect(confidenceChips([]).map((chip) => chip.label)).toContain("Evidence: stored reviews");
});

test("Readiness page keeps frozen exam-risk console selectors", () => {
    const src = componentSource();
    expect(src).toContain("Readiness - Exam Risk Console");
    expect(src).toContain("Are you ready to pass?");
    expect(src).not.toContain("surfaceClass=");
    expect(src).toContain("class=\"cfa-readiness__hero cfa-hero\"");
    expect(src).toContain("class=\"cfa-readiness__score-card\"");
    expect(src).toContain("cfa-readiness__console-grid");
    expect(src).toContain("class=\"cfa-readiness__retention-watch\"");
    expect(src).toContain("No blended number.");
});

test("Readiness page omits implementation-gap footer language", () => {
    const src = componentSource();
    expect(src).not.toContain("Production note:");
    expect(src).not.toContain("AI can explain");
    expect(src).not.toContain("Exact card IDs");
    expect(src).not.toContain("backend queue");
    expect(src).not.toContain("exact fading cards");
});

test("Readiness page routes top tabs and CTAs to existing bridge flows", () => {
    const src = componentSource();
    expect(READINESS_NAV.map((item) => item.cmd)).toStrictEqual([
        "cfa:home",
        "cfa:study",
        "cfa:conceptmap",
        "cfa:readiness",
        "cfa:progress",
        "cfa:sync",
    ]);
    for (const cmd of READINESS_NAV.map((item) => item.cmd)) {
        expect(cmd).toMatch(/^cfa:/);
    }
    for (const cmd of ["cfa:risk-session", "cfa:readiness-drill", "cfa:retention-queue"]) {
        expect(src).toContain(cmd);
    }
    expect(src).not.toContain("cfa:plan");
    expect(src).not.toContain("cfa:mock-schedule");
    expect(src).not.toContain("Begin 35-minute plan");
    expect(src).not.toContain("Schedule full mock");
    expect(src).toContain("on:navigate={(event) => go(event.detail)}");
});

test("Readiness page does not route latest mock review to an unsupported screen", () => {
    const src = componentSource();
    expect(src).not.toContain("cfa:mock-review");
    expect(src).not.toContain("Open latest mock review");
    expect(src).toContain("Mock review unavailable");
    expect(src).toContain("Latest mock review needs imported mock results");
    expect(src).toMatch(/disabled[\s\S]*aria-describedby="readiness-mock-unavailable"/);
});

test("Readiness page appbar tabs are visible on desktop", () => {
    const src = componentSource();
    expect(src).not.toContain("Desktop shell uses the native Qt toolbar");
    expect(src).toContain("ProductShellNav");
    expect(src).toContain("active=\"readiness\"");
    expect(src).not.toContain("surfaceClass=");
    expect(src).toContain("ariaLabel=\"CFA Readiness sections\"");
    expect(src).toContain("on:navigate={(event) => go(event.detail)}");
});

test("Readiness action cards reduce columns on mid-width desktop", () => {
    const src = componentSource();
    const start = src.indexOf("@media (max-width: 1120px)");
    const end = src.indexOf("@media (max-width: 980px)", start);
    const medium = src.slice(start, end);

    expect(medium).toMatch(/&__action-plan\s*\{[\s\S]*?grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);/);
});

test("Readiness phone media cardifies dense rows and keeps controls thumb-sized", () => {
    const src = componentSource();
    const mobile = src.slice(src.indexOf("@media (max-width: 720px)"));

    expect(src).toContain("data-label=\"Weight\"");
    expect(src).toContain("data-label=\"Reviewed / graded\"");
    expect(src).toContain("data-label=\"Recall signal\"");
    expect(src).toContain("data-label=\"Range\"");
    expect(productNavSource()).toMatch(/\.cfa-product-nav__tabs\s*\{[\s\S]*?overflow-x: auto;/);
    expect(mobile).toContain("width: 100%;");
    expect(mobile).toContain("min-height: 48px;");
    expect(mobile).toContain("grid-template-columns: minmax(120px, 0.7fr) minmax(0, 1fr);");
    expect(mobile).toContain("content: attr(data-label);");
    expect(mobile).toContain("height: auto;");
    expect(mobile).not.toContain("overflow-x: auto");
    expect(mobile).not.toContain("min-width: 640px");
});
