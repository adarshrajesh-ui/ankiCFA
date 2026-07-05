// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { assert, test } from "vitest";

import type { DeadlineRow } from "../types";
import {
    allNew,
    intervalCell,
    isAtRisk,
    newCardCount,
    newCardHint,
    recallCell,
    RISK_LABEL,
    riskMarker,
} from "./deadline";

function studied(recall: number, interval: number, warn = recall < 0.85): DeadlineRow {
    return {
        cardId: 1,
        predictedRecall: recall,
        suggestedIntervalDays: interval,
        warnLowRecall: warn,
        isNew: false,
    };
}

function fresh(): DeadlineRow {
    return { cardId: 2, predictedRecall: 0, suggestedIntervalDays: 0, warnLowRecall: false, isNew: true };
}

test("recallCell renders a studied card as a first-decimal percent", () => {
    assert.equal(recallCell(studied(0.834, 3)), "83.4%");
    assert.equal(recallCell(studied(0.6, 1)), "60.0%");
});

test("recallCell renders a NEW card as a calm 'New', never '0.0%'", () => {
    // The core Pass-2 fix: a never-studied card must not shout a false 0.0%.
    assert.equal(recallCell(fresh()), "New");
});

test("intervalCell renders an integer for studied, an en-dash for new", () => {
    assert.equal(intervalCell(studied(0.9, 12)), "12");
    assert.equal(intervalCell(fresh()), "–");
});

test("newCardCount and allNew classify the row set", () => {
    assert.equal(newCardCount([]), 0);
    assert.equal(newCardCount([studied(0.9, 4), fresh(), fresh()]), 2);
    assert.isFalse(allNew([]));
    assert.isFalse(allNew([studied(0.9, 4), fresh()]));
    assert.isTrue(allNew([fresh(), fresh()]));
});

test("newCardHint explains an all-new deck (the fresh-deck degenerate case)", () => {
    const hint = newCardHint([fresh(), fresh()]);
    assert.match(hint, /Every card here is new/);
    assert.match(hint, /once you've studied it/);
});

test("newCardHint explains a mixed deck with a correct count + plural", () => {
    assert.match(newCardHint([studied(0.9, 4), fresh(), fresh()]), /2 new cards are shown first/);
    assert.match(newCardHint([studied(0.9, 4), fresh()]), /1 new card is shown first/);
});

test("newCardHint is empty for a studied-only deck (no explanation needed)", () => {
    assert.equal(newCardHint([studied(0.9, 4), studied(0.5, 1)]), "");
});

// Pass-3 (ruthless) WCAG 1.4.1 Use of Color: the at-risk state must be carried
// by a redundant non-colour cue, not by the warn-orange colour alone.
test("isAtRisk flags a studied below-threshold card, never a new card", () => {
    assert.isTrue(isAtRisk(studied(0.6, 1))); // recall < 0.85 → warn
    assert.isFalse(isAtRisk(studied(0.9, 12))); // healthy studied card
    assert.isFalse(isAtRisk(fresh())); // a new card is never "at risk"
});

test("riskMarker returns a shape glyph only for at-risk rows", () => {
    // The shape (▲) is the non-colour cue a colour-blind reader relies on.
    assert.equal(riskMarker(studied(0.6, 1)), "▲");
    assert.equal(riskMarker(studied(0.9, 12)), "");
    assert.equal(riskMarker(fresh()), "");
});

test("RISK_LABEL is the redundant screen-reader label for an at-risk row", () => {
    assert.equal(RISK_LABEL, "at risk");
});
