// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Phase B (Pass 3, ruthless — desktop) capture + functional gate for the CFA
// Deadline planner's WCAG 2.1 SC 1.4.1 "Use of Color" fix (finding D-P3-3).
//
// The Deadline planner flags an at-risk row (predicted exam-day recall < 0.85)
// by colouring the figure warn-orange. Colour must not be the ONLY visual cue
// (Level A), so at-risk rows now also carry a non-colour SHAPE marker (▲) plus a
// screen-reader "at risk" label. This test boots the REAL backend with a
// populated (seeded) review history — so genuinely at-risk STUDIED cards exist,
// not just fresh "New" rows — navigates to the Deadline planner, and asserts
// every warn-coloured recall cell also carries the shape marker. Screens go to
// proof/…/desktop-ui/pass-3-colorcue/ as Phase-B evidence.
//
// Run seeded: `CFA_SEED_REVIEWS=1 CFA_UI_OUT=<dir> yarn test:e2e cfa_deadline_colorcue`.

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
        "pass-3-colorcue",
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
    expect(id, "the CFA first-launch seeder must have created a 'CFA Level II' deck")
        .not.toBeNull();
    return id as string;
}

test.beforeAll(() => {
    fs.mkdirSync(OUT, { recursive: true });
});

test.skip(!process.env.CFA_SEED_REVIEWS, "deadline color-cue gate requires CFA_SEED_REVIEWS=1");

test("at-risk Deadline rows carry a non-colour shape cue, not colour alone", async ({ page }) => {
    await page.goto("/cfa-home");
    const deckId = await cfaDeckId(page);

    await page.goto(`/cfa-deadline/${deckId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".cfa-page-heading__title")).toHaveText("Deadline planner");

    const table = page.locator(".cfa-table");
    await expect(table).toBeVisible();

    // With a seeded history there is at least one genuinely at-risk STUDIED card
    // (predicted recall < 0.85 → warn colour). If the seed produced none the test
    // is inconclusive for this finding, so require it.
    const warnCells = page.locator(".cfa-deadline__recall.is-warn");
    const warnCount = await warnCells.count();
    expect(warnCount, "a seeded deck must expose at least one at-risk (warn) row")
        .toBeGreaterThan(0);

    // THE FIX: every warn-coloured cell must ALSO carry the shape marker (▲), so
    // the at-risk state does not depend on the warn colour alone (WCAG 1.4.1).
    const markers = page.locator(".cfa-deadline__recall.is-warn .cfa-deadline__risk");
    await expect(markers).toHaveCount(warnCount);
    await expect(markers.first()).toHaveText("▲");

    // A healthy (non-warn) studied row must NOT carry the marker.
    const healthyMarker = page.locator(
        ".cfa-deadline__recall:not(.is-warn):not(.is-new) .cfa-deadline__risk",
    );
    await expect(healthyMarker).toHaveCount(0);

    // The at-risk STUDIED rows rank after the "New" rows inside the scrollable
    // table, so scroll the first warn cell into view before capturing evidence.
    await warnCells.first().scrollIntoViewIfNeeded();
    await page.screenshot({
        path: path.join(OUT, "01-cfa-deadline-colorcue.png"),
        fullPage: true,
    });
});
