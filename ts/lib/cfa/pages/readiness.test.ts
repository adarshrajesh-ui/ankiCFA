// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";

import type { TopicRow } from "../types";
import { captionText, noRecallYet, topicRows } from "./readiness";

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
