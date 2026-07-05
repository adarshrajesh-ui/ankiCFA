// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";

import type { CfaHomePayload, TopicRow } from "../types";
import {
    buildPriorityRisks,
    homeMetricChips,
    recommendedSessions,
    shortTopicName,
    syncChipLabel,
} from "./home";

function topic(over: Partial<TopicRow>): TopicRow {
    return {
        topic: "Equity Investments",
        weight: 0.125,
        reviewedCards: 10,
        gradedReviews: 40,
        recallRange: { low: 0.7, high: 0.8 },
        covered: true,
        ...over,
    };
}

function payload(over: Partial<CfaHomePayload> = {}): CfaHomePayload {
    return {
        deckName: "CFA Level II",
        heroMode: "abstain",
        heroAbstain: { reason: "Not enough graded reviews", readinessLabel: "Readiness" },
        memory: {
            name: "Memory",
            meaning: "Memory strength",
            abstain: true,
            reason: "Not enough graded reviews",
            point: null,
            rangeLow: null,
            rangeHigh: null,
        },
        performance: {
            name: "Performance",
            meaning: "First-exposure accuracy",
            abstain: true,
            reason: "Not enough first exposures",
            point: null,
            rangeLow: null,
            rangeHigh: null,
        },
        readiness: {
            name: "Readiness",
            label: "No call",
            meaning: "Exam readiness",
            abstain: true,
            reason: "Not enough evidence",
            point: null,
            rangeLow: null,
            rangeHigh: null,
        },
        caption: {
            coveragePct: 0.71,
            topicsCovered: 7,
            topicsTotal: 10,
            gradedReviews: 1842,
            firstExposures: 320,
            lastReviewAt: null,
        },
        topics: [],
        footerText: "Scores use existing CFA readiness data.",
        examDate: "2026-08-25",
        daysToExam: 42,
        aiEnabled: true,
        sync: {
            connected: true,
            syncing: false,
            status: "Connected",
            tone: "pass",
            account: "learner@example.com",
            lastSyncedAt: "2026-07-05T14:32:00",
            lastSyncedLabel: "14:32",
            endpoint: "AnkiWeb",
            detail: "Ready",
            actionLabel: "Sync now",
        },
        ...over,
    };
}

test("homeMetricChips: formats frozen hero metrics from the existing payload", () => {
    expect(homeMetricChips(payload())).toStrictEqual([
        "42 days to exam",
        "1,842 graded reviews",
        "71% topic coverage",
        "AI explanations ready",
    ]);
});

test("syncChipLabel: shows connect action when no account is present", () => {
    expect(syncChipLabel(payload({ sync: { ...payload().sync, connected: false } }))).toBe("Connect & Sync");
});

test("buildPriorityRisks: sorts heavy weak topics ahead of mastered topics", () => {
    const risks = buildPriorityRisks([
        topic({ topic: "Ethics & Professional Standards", weight: 0.125, recallRange: { low: 0.86, high: 0.92 } }),
        topic({ topic: "Financial Reporting & Analysis", weight: 0.125, recallRange: { low: 0.28, high: 0.4 } }),
        topic({ topic: "Derivatives", weight: 0.075, recallRange: null }),
    ]);
    expect(risks[0].topic).toBe("Financial Reporting & Analysis");
    expect(risks[0].label).toBe("High risk");
    expect(risks[0].shortTopic).toBe("FRA");
});

test("recommendedSessions: derives Home cards without changing study logic", () => {
    const risks = buildPriorityRisks([
        topic({ topic: "Financial Reporting & Analysis", weight: 0.125, recallRange: { low: 0.28, high: 0.4 } }),
        topic({ topic: "Ethics & Professional Standards", weight: 0.125, recallRange: { low: 0.86, high: 0.92 } }),
    ]);
    const sessions = recommendedSessions(risks, [
        topic({ topic: "Financial Reporting & Analysis", weight: 0.125, recallRange: { low: 0.28, high: 0.4 } }),
        topic({ topic: "Ethics & Professional Standards", weight: 0.125, recallRange: { low: 0.86, high: 0.92 } }),
    ]);
    expect(sessions[0].title).toBe("25-card FRA priority session");
    expect(sessions[0].meta).toMatch(/existing weakest-first priority study/);
    expect(sessions[1].title).toBe("10-card Ethics retention pass");
});

test("shortTopicName: keeps unknown topics readable", () => {
    expect(shortTopicName("Some Future Topic")).toBe("Some Future Topic");
});
