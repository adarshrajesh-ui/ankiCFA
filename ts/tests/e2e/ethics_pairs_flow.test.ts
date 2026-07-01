// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import fs from "node:fs";
import path from "node:path";

import { expect, test } from "./fixtures";

// Renders the real CFA Ethics Minimal-Pair FRONT template with a sample pair substituted in,
// then verifies the three non-negotiables of the flow:
//   1. both vignettes are co-presented (visible at once),
//   2. the governing Standard is NOT revealed before the attempt,
//   3. it is revealed only after both judgments AND the decisive-fact MCQ are answered.
// Uses page.setContent (no Anki boot required for this file).

const REPO = process.cwd();
const FEATURE = path.join(REPO, "cfa", "ethics_pairs");

function loadFirstPair(): Record<string, string> {
    const line = fs.readFileSync(path.join(FEATURE, "pairs.jsonl"), "utf-8").split("\n").find((l) => l.trim());
    if (!line) { throw new Error("pairs.jsonl is empty"); }
    return JSON.parse(line);
}

function renderFront(pair: Record<string, any>): string {
    const front = fs.readFileSync(path.join(FEATURE, "templates", "front.html"), "utf-8");
    const css = fs.readFileSync(path.join(FEATURE, "templates", "style.css"), "utf-8");
    const fields: Record<string, string> = {
        PairId: pair.pair_id,
        ClusterTag: `cluster::${pair.cluster}`,
        VignetteA: pair.vignette_a,
        VignetteB: pair.vignette_b,
        AnswerA: pair.answer_a,
        AnswerB: pair.answer_b,
        DecisiveFact: pair.decisive_fact,
        DistractorFact1: pair.distractors[0],
        DistractorFact2: pair.distractors[1],
        DistractorFact3: pair.distractors[2],
        Standard: pair.standard,
        Rationale: pair.rationale,
    };
    let html = front;
    for (const [k, v] of Object.entries(fields)) {
        html = html.split(`{{${k}}}`).join(v);
    }
    return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body class="card">${html}</body></html>`;
}

test("minimal-pair renders both vignettes and hides the Standard until the attempt is complete", async ({ page }) => {
    const pair = loadFirstPair();
    await page.setContent(renderFront(pair));

    // 1. both cases co-presented
    await expect(page.locator("#cfa-cases .cfa-case")).toHaveCount(2);
    const cases = page.locator("#cfa-cases");
    await expect(cases).toContainText(pair.vignette_a.slice(0, 40));
    await expect(cases).toContainText(pair.vignette_b.slice(0, 40));

    // 2. the Standard is NOT revealed before the attempt
    const reveal = page.locator("#cfa-reveal");
    await expect(reveal).toBeHidden();
    await expect(page.getByText(pair.standard, { exact: false })).toBeHidden(); // only in hidden source block
    await expect(page.locator("#cfa-check")).toBeDisabled();

    // partial attempt (only one judgment) must NOT enable reveal
    await page.locator(`.cfa-case[data-case="A"] .cfa-judge-btn[data-j="${pair.answer_a}"]`).click();
    await expect(page.locator("#cfa-check")).toBeDisabled();
    await expect(reveal).toBeHidden();

    // 3. complete the attempt: both judgments + the decisive fact
    await page.locator(`.cfa-case[data-case="B"] .cfa-judge-btn[data-j="${pair.answer_b}"]`).click();
    await page.locator("#cfa-options .cfa-opt[data-correct=\"1\"]").click();
    await expect(page.locator("#cfa-check")).toBeEnabled();
    await page.locator("#cfa-check").click();

    // now — and only now — the Standard + rationale are revealed
    await expect(reveal).toBeVisible();
    await expect(reveal).toContainText(pair.standard);
    await expect(reveal).toContainText("Fully correct"); // we answered correctly
    await expect(page.locator("#cfa-record")).toBeVisible();
});
