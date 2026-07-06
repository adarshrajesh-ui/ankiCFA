// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Phase B — desktop Pass 2 (harsher): the POPULATED render of the CFA Home +
// Exam Readiness web surfaces.
//
// The Pass-1 gate (cfa_readiness_render.test.ts) proves the pages render the
// honest zero-review ABSTAIN state on a fresh profile. This test proves the
// other half of the named must-fix ("render the three scores, ranges, and
// coverage map with real data"): the state a RETURNING learner sees, with a
// real graded review history behind it → real score ranges and a lit-up
// coverage map, NOT abstain.
//
// It requires the launcher to have pre-seeded a populated collection, so it is
// NOT part of the default `just test-e2e` run (that would flip the abstain
// asserts red). Run it in isolation with the review history seeded:
//
//   CFA_SEED_REVIEWS=1 CFA_UI_OUT=proof/friday/gnhf-speedrun/desktop-ui/pass-2 \
//     out/extracted/node/bin/node node_modules/.bin/playwright test \
//     cfa_readiness_populated
//
// The data is real: `qt/tests/launch_anki_for_e2e.py` seeds the shared engine
// via `tools/cfa/seed_reviews.py`, whose numbers are computed by the same Rust
// ComputeCfaScores RPC the app uses — honest evidence, not a static mock.

import type { Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { expect, test } from "./fixtures";

const OUT = process.env.CFA_UI_OUT
    ? path.resolve(process.env.CFA_UI_OUT)
    : path.join(
        process.cwd(),
        "proof",
        "friday",
        "gnhf-speedrun",
        "desktop-ui",
        "pass-2",
    );

/** Resolve the seeded "CFA Level II" deck id via the getDeckNames RPC. */
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
    expect(id, "the launcher must have pre-seeded a 'CFA Level II' deck")
        .not.toBeNull();
    return id as string;
}

test.beforeAll(() => {
    fs.mkdirSync(OUT, { recursive: true });
});

test.skip(!process.env.CFA_SEED_REVIEWS, "populated render gate requires CFA_SEED_REVIEWS=1");

test("CFA Home renders the populated Command Center state with a study history", async ({ page }) => {
    await page.goto("/cfa-home");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Today’s work" })).toBeVisible();
    await expect(page.getByText("Home · CFA Command Center")).toBeVisible();

    const metrics = page.getByLabel("Current CFA metrics");
    await expect(metrics.getByText(/[1-9]\d* graded reviews/)).toBeVisible();
    await expect(metrics.getByText(/[1-9]\d*% topic coverage/)).toBeVisible();
    await expect(metrics.getByText("Local explanations ready")).toBeVisible();

    await expect(page.getByText("Priority risk")).toBeVisible();
    await expect(page.getByText("Concept Map preview")).toBeVisible();
    await expect(page.getByRole("group", { name: "Interactive Concept Map preview" })).toBeVisible();

    // The populated state must NOT show the abstain microcopy anywhere.
    await expect(page.getByText(/Not enough data/)).toHaveCount(0);
    await expect(page.getByText("Awaiting reviews")).toHaveCount(0);

    await page.screenshot({
        path: path.join(OUT, "01-cfa-home-populated.png"),
        fullPage: true,
    });
});

test("Exam Readiness renders real ranges + a lit coverage map", async ({ page }) => {
    await page.goto("/cfa-home");
    const deckId = await cfaDeckId(page);

    await page.goto(`/cfa-readiness/${deckId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".cfa-product-nav__brand small")).toHaveText("CFA Level II");
    await expect(page.locator(".cfa-hero")).toBeVisible();

    // Not the abstain hero.
    await expect(page.getByText(/No pass\/fail call yet/)).toHaveCount(0);
    await expect(page.getByText(/Not enough data/)).toHaveCount(0);
    await expect(page.getByText("Awaiting reviews")).toHaveCount(0);

    // Three real score cards, each with a whole-number low-high range.
    await expect(page.locator(".cfa-stat")).toHaveCount(3);
    await expect(page.locator(".cfa-stat.abstain")).toHaveCount(0);
    await expect(page.locator(".cfa-stat", { hasText: /\d+-\d+/ }).first()).toBeVisible();

    // The coverage map now has real per-topic recall data (the empty-state hint
    // must be gone), and still lists every canonical area + weight.
    const table = page.locator(".cfa-table");
    await expect(table).toBeVisible();
    await expect(page.locator(".cfa-readiness__table-hint")).toHaveCount(0);
    await expect(table.getByText("Fixed Income", { exact: true })).toBeVisible();
    await expect(table.locator(".cfa-readiness__topic-stat[data-label=\"Weight\"]").getByText("12%").first())
        .toBeVisible();

    await page.screenshot({
        path: path.join(OUT, "02-cfa-readiness-populated.png"),
        fullPage: true,
    });
});
