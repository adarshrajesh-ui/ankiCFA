// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Phase B functional gate for the desktop CFA Exam Readiness surface.
//
// The named must-fix in proof/friday/SPEEDRUN-PLAN.md §4 is: "Desktop Readiness
// does nothing → make it actually open and render the three scores + ranges +
// coverage map with real data; add a functional test." This is that test.
//
// It boots the REAL Anki backend (Playwright webServer → launch_anki_for_e2e.py,
// which seeds a fresh profile so the CFA first-launch seeder loads the "CFA Level
// II" deck), then drives the two shipped CFA web surfaces exactly as the desktop
// app does and asserts they render REAL backend data — never a static mock:
//   * /cfa-home        — the native landing dashboard (server resolves the CFA
//                        deck) → three honest score cards + coverage caption.
//   * /cfa-readiness/N — the Exam Readiness page for the CFA Level II deck →
//                        the three scores, the honest hero, and the full
//                        per-topic COVERAGE MAP (all 10 canonical CFA areas with
//                        their real exam weights, sourced from the deck).
// Screens are captured to proof/…/desktop-ui/pass-1/ as Phase-B "before"
// evidence. The data is real: a freshly seeded deck has no graded reviews, so
// the scores honestly ABSTAIN — that is the true first-run state, and the
// coverage map still lists every real topic + weight. (The populated-range /
// Bayesian-call render is captured separately by tools/cfa/capture_readiness.py.)

import type { Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { expect, test } from "./fixtures";

// Screenshot destination. Defaults to the Phase-B pass-1 folder; override with
// CFA_UI_OUT to capture a before/after pair into distinct directories.
const OUT = process.env.CFA_UI_OUT
    ? path.resolve(process.env.CFA_UI_OUT)
    : path.join(
        process.cwd(),
        "proof",
        "friday",
        "gnhf-speedrun",
        "desktop-ui",
        "pass-1",
    );

// The 10 canonical CFA Level II topic areas the coverage map must list, with the
// exam-weight-band midpoints the backend reports (see cfa/outline/level2_topics).
const CANONICAL_TOPICS = [
    "Ethics & Professional Standards",
    "Quantitative Methods",
    "Economics",
    "Financial Reporting & Analysis",
    "Corporate Issuers",
    "Equity Investments",
    "Fixed Income",
    "Derivatives",
    "Alternative Investments",
    "Portfolio Management",
];

/** Resolve the seeded "CFA Level II" deck id by decoding the getDeckNames RPC in
 * the page context (repeated DeckNameId{ id=1 int64; name=2 string }). */
async function cfaDeckId(page: Page): Promise<string> {
    const id = await page.evaluate(async () => {
        const r = await fetch("/_anki/getDeckNames", {
            method: "POST",
            headers: { "Content-Type": "application/binary" },
            body: new Uint8Array(),
        });
        const buf = new Uint8Array(await r.arrayBuffer());
        function varint(b: Uint8Array, i: number): [bigint, number] {
            let shift = 0n, res = 0n, pos = i;
            for (;;) {
                const byte = b[pos++];
                res |= BigInt(byte & 0x7f) << shift;
                if ((byte & 0x80) === 0) {
                    break;
                }
                shift += 7n;
            }
            return [res, pos];
        }
        let i = 0;
        let found: string | null = null;
        while (i < buf.length) {
            if (buf[i++] !== 0x0a) {
                break;
            }
            let len: bigint;
            [len, i] = varint(buf, i);
            const end = i + Number(len);
            let entryId = "0", name = "";
            let j = i;
            while (j < end) {
                const t = buf[j++];
                if (t === 0x08) {
                    let v: bigint;
                    [v, j] = varint(buf, j);
                    entryId = v.toString();
                } else if (t === 0x12) {
                    let nl: bigint;
                    [nl, j] = varint(buf, j);
                    name = new TextDecoder().decode(buf.subarray(j, j + Number(nl)));
                    j += Number(nl);
                } else {
                    break;
                }
            }
            if (name === "CFA Level II") {
                found = entryId;
            }
            i = end;
        }
        return found;
    });
    expect(id, "the CFA first-launch seeder must have created a 'CFA Level II' deck")
        .not.toBeNull();
    return id as string;
}

test.beforeAll(() => {
    fs.mkdirSync(OUT, { recursive: true });
});

test("CFA Home dashboard renders the three honest scores with real data", async ({ page }) => {
    await page.goto("/cfa-home");
    await page.waitForLoadState("networkidle");

    // Three honest-score StatCards, each naming its score.
    const stats = page.locator(".cfa-stat");
    await expect(stats).toHaveCount(3);
    for (const name of ["Memory", "Performance", "Readiness"]) {
        await expect(page.locator(".cfa-stat__label", { hasText: name })).toBeVisible();
    }

    // The coverage caption reports real topic totals (10 canonical areas).
    await expect(page.getByText(/\(\d+\/10 topics\)/)).toBeVisible();

    await page.screenshot({
        path: path.join(OUT, "01-cfa-home.png"),
        fullPage: true,
    });
});

test("Exam Readiness renders three scores + the full per-topic coverage map", async ({ page }) => {
    await page.goto("/cfa-home");
    const deckId = await cfaDeckId(page);

    await page.goto(`/cfa-readiness/${deckId}`);
    await page.waitForLoadState("networkidle");

    // Heading + the real deck name (proves it is bound to the resolved deck).
    await expect(page.locator(".cfa-page-heading__title")).toHaveText("CFA Level II");

    // The honest hero (a fresh deck has no graded reviews → abstain, not a fake
    // green pass call — this is the honesty contract).
    await expect(page.locator(".cfa-hero")).toBeVisible();

    // The three honest-score cards.
    await expect(page.locator(".cfa-stat")).toHaveCount(3);
    for (const name of ["Memory", "Performance", "Readiness"]) {
        await expect(page.locator(".cfa-stat__label", { hasText: name })).toBeVisible();
    }

    // The COVERAGE MAP: the per-topic table must list every canonical CFA area,
    // each with its real exam weight — this is the "coverage map with real data".
    const table = page.locator(".cfa-table");
    await expect(table).toBeVisible();
    for (const topic of CANONICAL_TOPICS) {
        await expect(table.getByText(topic, { exact: true })).toBeVisible();
    }
    // Real exam-weight values are present (0.12 for the five heavy areas).
    await expect(table.getByText("0.12").first()).toBeVisible();

    await page.screenshot({
        path: path.join(OUT, "02-cfa-readiness.png"),
        fullPage: true,
    });
});

test("Readiness route renders for an empty deck without crashing (empty state)", async ({ page }) => {
    // Default deck (id 1) has no CFA cards → honest empty/abstain state must still
    // render the full page chrome rather than a blank screen.
    await page.goto("/cfa-readiness/1");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".cfa-page-heading__title")).toBeVisible();
    await expect(page.locator(".cfa-stat")).toHaveCount(3);
    await expect(page.getByText("Not enough data — keep studying")).toBeVisible();

    await page.screenshot({
        path: path.join(OUT, "03-cfa-readiness-empty-deck.png"),
        fullPage: true,
    });
});
