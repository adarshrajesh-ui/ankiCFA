// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Pure helpers for the CFA Home dashboard: the exam countdown line and the CTA
// list. No DOM/Svelte — data → display strings + tones, so it stays trivially
// testable and the CTAs are declared in one place.
// -----------------------------------------------------------------------------

import type { CfaHomePayload, CfaTone, TopicRow } from "../types";

import { productNavItems } from "../productNav";
import { masteryFromTopic } from "./conceptmap";
import { formatHeroAbstainReason } from "./evidence";

/** A dashboard call-to-action. `cmd` is the bridgeCommand the Qt side routes. */
export interface HomeCta {
    cmd: string;
    label: string;
    sub: string;
    primary?: boolean;
}

/**
 * The primary study/report CTAs. Each `cmd` is dispatched to the existing CFA
 * entry points by aqt/cfa_home.py's bridge handler (no new study logic here).
 */
export const HOME_CTAS: HomeCta[] = [
    {
        cmd: "cfa:ethics",
        label: "Study Ethics — Minimal Pairs",
        sub: "The flagship ethics discrimination drill",
        primary: true,
    },
    {
        cmd: "cfa:priority",
        label: "Study by Exam Priority",
        sub: "Weakest, heaviest-weighted cards first",
    },
    {
        cmd: "cfa:study",
        label: "Study the CFA deck",
        sub: "Open the CFA Level II deck",
    },
    {
        cmd: "cfa:readiness",
        label: "Exam Readiness",
        sub: "The honest pass / fail report",
    },
    {
        cmd: "cfa:deadline",
        label: "Peak on Exam Day",
        sub: "Deadline-aware review plan",
    },
];

/** The shared phone/desktop product-nav destinations. */
export const HOME_NAV = productNavItems("home");

export interface HomeRisk {
    topic: string;
    shortTopic: string;
    detail: string;
    label: string;
    tone: "risk" | "watch" | "maintain";
    priority: number;
    mastery: number | null;
    weight: number;
    gradedReviews: number;
}

export interface HomeSession {
    eyebrow: string;
    title: string;
    detail: string;
    meta: string;
    impactPct: number;
}

function integer(n: number): string {
    return n.toLocaleString("en-US");
}

function pct(x: number | null | undefined): string {
    return x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`;
}

function recallRange(row: TopicRow): string {
    return row.recallRange === null
        ? "no recall range yet"
        : `${pct(row.recallRange.low)}–${pct(row.recallRange.high)} recall`;
}

export function shortTopicName(topic: string): string {
    const known: Record<string, string> = {
        "Alternative Investments": "Alt Inv",
        "Corporate Issuers": "Corp",
        "Derivatives": "Derivatives",
        "Economics": "Econ",
        "Equity Investments": "Equity",
        "Ethics & Professional Standards": "Ethics",
        "Financial Reporting & Analysis": "FRA",
        "Financial Reporting Analysis": "FRA",
        "Fixed Income": "Fixed Income",
        "Portfolio Management": "Portfolio",
        "Quantitative Methods": "Quant",
    };
    return known[topic] ?? topic;
}

function riskLabel(priority: number, mastery: number | null): Pick<HomeRisk, "label" | "tone"> {
    if (mastery !== null && mastery >= 0.7) {
        return { label: "Maintain", tone: "maintain" };
    }
    if (mastery === null || mastery < 0.45 || priority >= 0.07) {
        return { label: "High risk", tone: "risk" };
    }
    return { label: "Med risk", tone: "watch" };
}

export function buildPriorityRisks(topics: TopicRow[], limit = 3): HomeRisk[] {
    return [...topics]
        .map((topic) => {
            const mastery = masteryFromTopic(topic);
            const weakness = mastery === null ? 0.72 : 1 - mastery;
            const priority = topic.weight * weakness;
            const label = riskLabel(priority, mastery);
            return {
                topic: topic.topic,
                shortTopic: shortTopicName(topic.topic),
                detail: `${recallRange(topic)} · ${integer(topic.gradedReviews)} graded reviews · ${
                    pct(topic.weight)
                } exam weight.`,
                priority,
                mastery,
                weight: topic.weight,
                gradedReviews: topic.gradedReviews,
                ...label,
            };
        })
        .sort((a, b) => b.priority - a.priority || b.weight - a.weight || a.topic.localeCompare(b.topic))
        .slice(0, limit);
}

export function homeMetricChips(data: CfaHomePayload): string[] {
    let days = "Exam date unset";
    if (data.daysToExam === 1) {
        days = "1 day to exam";
    } else if (data.daysToExam !== null) {
        days = `${data.daysToExam} days to exam`;
    }
    return [
        days,
        `${integer(data.caption.gradedReviews)} graded reviews`,
        `${pct(data.caption.coveragePct)} topic coverage`,
        "Local explanations ready",
    ];
}

export function syncChipLabel(data: CfaHomePayload): string {
    if (!data.sync.connected) {
        return "Connect & Sync";
    }
    return data.sync.lastSyncedAt ? `Synced ${data.sync.lastSyncedLabel}` : "Sync ready";
}

/**
 * The plain post-sync result line for the Home hero: names the active account +
 * endpoint and whether the last sync changed anything, so "I don't think it did
 * anything" and an account mismatch both become verifiable. Falls back to a
 * derived line if the backend hasn't supplied `resultLabel`.
 */
export function syncSummary(data: CfaHomePayload): string {
    const s = data.sync;
    if (s.resultLabel) {
        return s.resultLabel;
    }
    if (!s.connected) {
        return "Connect this device to sync your CFA progress across devices.";
    }
    const who = s.account && s.account !== "Not connected" ? s.account : "your sync account";
    if (!s.lastSyncedAt) {
        return `Signed in as ${who} (${s.endpoint}). Sync now to update this device.`;
    }
    return `Synced as ${who} (${s.endpoint}).`;
}

export function commandCenterLead(data: CfaHomePayload): string {
    if (data.heroMode === "bayesian_call" && data.heroBayesian) {
        return `Current call: ${data.heroBayesian.call} (p=${
            data.heroBayesian.callProb.toFixed(2)
        }). The next session is built from the weakest exam-weighted topics.`;
    }
    if (data.heroAbstain) {
        const reason = formatHeroAbstainReason(data.heroAbstain.reason, data.caption);
        return `${reason}. The priority queue remains available while the scores gather evidence.`;
    }
    return "A focused starting point: the next session, the weak areas driving it, and quick access to the Concept Map.";
}

function sessionCardCount(risk: HomeRisk | undefined, fallback: number): number {
    if (!risk) {
        return fallback;
    }
    if (risk.tone === "risk") {
        return 25;
    }
    if (risk.tone === "watch") {
        return 18;
    }
    return 10;
}

export function recommendedSessions(risks: HomeRisk[], topics: TopicRow[]): HomeSession[] {
    const primary = risks[0];
    const maintenanceTopic = [...topics]
        .map((topic) => ({ topic, mastery: masteryFromTopic(topic) }))
        .filter((row) => row.mastery !== null)
        .sort((a, b) => (b.mastery ?? 0) - (a.mastery ?? 0) || b.topic.weight - a.topic.weight)[0]?.topic;
    const maintenanceName = maintenanceTopic ? shortTopicName(maintenanceTopic.topic) : "Ethics";

    return [
        {
            eyebrow: "Recommended session",
            title: `${sessionCardCount(primary, 25)}-card ${primary?.shortTopic ?? "exam"} priority session`,
            detail: primary
                ? `Highest expected readiness lift from current topic evidence: ${primary.detail}`
                : "Uses the existing exam-priority queue when topic evidence is still sparse.",
            meta: "Routes to existing weakest-first priority study",
            impactPct: primary ? Math.max(42, Math.min(92, Math.round(primary.priority * 900))) : 62,
        },
        {
            eyebrow: "Maintenance",
            title: `10-card ${maintenanceName} retention pass`,
            detail: "A short pass for the strongest available node so high-weight material stays fresh.",
            meta: "Maintenance target is derived from current mastery data",
            impactPct: 48,
        },
    ];
}

/** Days at or under which the countdown turns warn-coloured. */
export const EXAM_SOON_DAYS = 14;

export interface Countdown {
    headline: string;
    sub: string;
    tone: CfaTone;
    /** True when no exam date is configured yet (prompt the user to set one). */
    unset: boolean;
}

/** The exam countdown banner text/tone from the Home payload. */
export function examCountdown(p: CfaHomePayload): Countdown {
    if (p.daysToExam === null || p.examDate === null) {
        // A missing exam date is a calm prompt, not a warning: keep it neutral
        // navy so the loud warn-orange is reserved for a genuinely near deadline
        // and the warm primary CTA remains the single accent that leads the eye.
        return {
            headline: "Set your exam date",
            sub: "Schedule it from Exam Readiness or Peak on Exam Day.",
            tone: "neutral",
            unset: true,
        };
    }
    const d = p.daysToExam;
    let headline: string;
    if (d === 0) {
        headline = "Exam day is here";
    } else if (d === 1) {
        headline = "1 day to the exam";
    } else {
        headline = `${d} days to the exam`;
    }
    const tone: CfaTone = d <= EXAM_SOON_DAYS ? "warn" : "neutral";
    return { headline, sub: `CFA Level II · ${p.examDate}`, tone, unset: false };
}

/** Short one-liner summarising the pass/fail hero for the countdown lead. */
export function heroLead(p: CfaHomePayload): string {
    if (p.heroMode === "bayesian_call" && p.heroBayesian) {
        return `Current call: ${p.heroBayesian.call} (p=${p.heroBayesian.callProb.toFixed(2)}).`;
    }
    if (p.heroAbstain) {
        const reason = formatHeroAbstainReason(p.heroAbstain.reason, p.caption);
        return `${reason} — keep studying to unlock a pass/fail call.`;
    }
    return "Keep studying to build an honest pass/fail estimate.";
}
