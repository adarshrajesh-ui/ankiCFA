// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Pure helpers for the CFA Home dashboard: the exam countdown line and the CTA
// list. No DOM/Svelte — data → display strings + tones, so it stays trivially
// testable and the CTAs are declared in one place.
// -----------------------------------------------------------------------------

import type { CfaHomePayload, CfaTone } from "../types";

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
        return `${p.heroAbstain.reason} — keep studying to unlock a pass/fail call.`;
    }
    return "Keep studying to build an honest pass/fail estimate.";
}
