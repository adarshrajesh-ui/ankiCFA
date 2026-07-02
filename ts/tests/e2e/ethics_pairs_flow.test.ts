// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import fs from "node:fs";
import path from "node:path";

import { expect, test } from "./fixtures";

// Renders the real CFA Ethics Minimal-Pair FRONT template with a sample pair substituted in,
// then verifies the four non-negotiables of the tap-to-highlight flow:
//   1. both vignettes are co-presented as tokenized, tappable paragraphs,
//   2. the governing Standard is NOT revealed before the attempt,
//   3. Check stays disabled until BOTH judgments AND an in-vignette highlight are supplied,
//   4. once the decisive phrase is highlighted in the violating case, Check reveals the grade,
//      the gold phrase, the governing Standard and the rationale ("Fully correct").
// Uses page.setContent (no Anki boot required for this file).

const REPO = process.cwd();
const FEATURE = path.join(REPO, "cfa", "ethics_pairs");

// --- highlight tokenizer, mirrored from the shared CFA-HIGHLIGHT block (front.html /
//     highlight_logic.js / ethics_scoring.py) so the test can locate the gold token indices the
//     same way the template does. -------------------------------------------------------------
const STRIP_CHARS = ".,;:!?\"'()[]{}…-–—‘’“”";
function stripToken(tok: string): string {
    let s = 0, e = tok.length;
    while (s < e && STRIP_CHARS.indexOf(tok.charAt(s)) !== -1) s++;
    while (e > s && STRIP_CHARS.indexOf(tok.charAt(e - 1)) !== -1) e--;
    return tok.slice(s, e).toLowerCase();
}
function tokenize(text: string): string[] {
    const t = (text ?? "").replace(/^\s+|\s+$/g, "");
    return t === "" ? [] : t.split(/\s+/);
}
function normalizedTokens(text: string): string[] {
    return tokenize(text).map(stripToken);
}
function findGoldIndices(vignette: string, gold: string): number[] {
    const v = normalizedTokens(vignette), g = normalizedTokens(gold);
    if (g.length === 0) return [];
    for (let start = 0; start + g.length <= v.length; start++) {
        let ok = true;
        for (let k = 0; k < g.length; k++) {
            if (v[start + k] !== g[k]) { ok = false; break; }
        }
        if (ok) return Array.from({ length: g.length }, (_, j) => start + j);
    }
    return [];
}

function loadFirstPair(): Record<string, any> {
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
        DecisivePhrase: pair.decisive_phrase,
        DecisivePhraseCase: pair.decisive_phrase_case,
        Standard: pair.standard,
        Rationale: pair.rationale,
    };
    let html = front;
    for (const [k, v] of Object.entries(fields)) {
        html = html.split(`{{${k}}}`).join(v);
    }
    return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body class="card">${html}</body></html>`;
}

test("minimal-pair co-presents both vignettes and hides the Standard until judgments + highlight are complete", async ({ page }) => {
    const pair = loadFirstPair();
    await page.setContent(renderFront(pair));

    // 1. both cases co-presented as tokenized paragraphs
    await expect(page.locator("#cfa-cases .cfa-case")).toHaveCount(2);
    const cases = page.locator("#cfa-cases");
    await expect(cases).toContainText(pair.vignette_a.slice(0, 40));
    await expect(cases).toContainText(pair.vignette_b.slice(0, 40));
    // every vignette word is a tappable token span
    await expect(page.locator(".cfa-vignette .cfa-tok").first()).toBeVisible();

    // 2. the Standard is NOT revealed before the attempt
    const reveal = page.locator("#cfa-reveal");
    await expect(reveal).toBeHidden();
    await expect(page.getByText(pair.standard, { exact: false })).toBeHidden(); // only in hidden source block
    await expect(page.locator("#cfa-check")).toBeDisabled();

    // partial attempt (only one judgment, no highlight) must NOT enable Check
    await page.locator(`.cfa-case[data-case="A"] .cfa-judge-btn[data-j="${pair.answer_a}"]`).click();
    await expect(page.locator("#cfa-check")).toBeDisabled();
    await expect(reveal).toBeHidden();

    // 3. both judgments still not enough — the highlight is required too
    await page.locator(`.cfa-case[data-case="B"] .cfa-judge-btn[data-j="${pair.answer_b}"]`).click();
    await expect(page.locator("#cfa-check")).toBeDisabled();

    // 4. highlight the decisive phrase in the violating (decisive) vignette by tapping its first
    //    and last word — tap-then-tap selects the inclusive range between them.
    const decisiveCase = String(pair.decisive_phrase_case).toUpperCase();
    const decisiveVignette = decisiveCase === "B" ? pair.vignette_b : pair.vignette_a;
    const gold = findGoldIndices(decisiveVignette, pair.decisive_phrase);
    expect(gold.length).toBeGreaterThan(0);
    const panel = page.locator(`.cfa-case[data-case="${decisiveCase}"]`);
    await panel.locator(`.cfa-tok[data-i="${gold[0]}"]`).click();
    await panel.locator(`.cfa-tok[data-i="${gold[gold.length - 1]}"]`).click();
    // the selected span is painted
    await expect(panel.locator(".cfa-tok.sel")).toHaveCount(gold.length);

    // now Check is enabled; clicking it reveals the grade — and only now the Standard.
    await expect(page.locator("#cfa-check")).toBeEnabled();
    await page.locator("#cfa-check").click();

    await expect(reveal).toBeVisible();
    await expect(reveal).toContainText(pair.standard);
    await expect(reveal).toContainText("Fully correct"); // exact-gold highlight + right judgments
    await expect(reveal).toContainText(pair.decisive_phrase); // gold phrase shown on reveal
    await expect(page.locator("#cfa-record")).toBeVisible();
});
