// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Phase B (Pass 2, desktop) capture + functional gate for the CFA Deadline
// planner surface (D3 in proof/friday/UI-INVENTORY.md).
//
// The "Peak on exam day" Deadline planner (`/cfa-deadline/{deckId}` →
// CfaDeadlinePage.svelte) is a shipped desktop surface that had never been
// captured or critiqued in any Phase-B pass. This test boots the REAL backend
// (Playwright webServer → launch_anki_for_e2e.py, which seeds a fresh profile so
// the CFA first-launch seeder loads the "CFA Level II" deck) and drives the page
// exactly as the desktop DeadlineDialog does, asserting it renders REAL backend
// data (never a static mock) in both states the inventory calls for:
//   * ranked   — the CFA Level II deck: a weakest-first table of predicted
//                exam-day recall + capped intervals for its due/new cards.
//   * empty    — the Default deck (no CFA cards): the honest "No due cards to
//                rank yet." notice + helper caption, full page chrome intact.
// Screens are captured to proof/…/desktop-ui/pass-2/ as Phase-B evidence.

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

test.skip(!!process.env.CFA_SEED_REVIEWS, "fresh Deadline render gate requires an unseeded profile");

test("Deadline planner ranks the CFA deck weakest-first with real data", async ({ page }) => {
    await page.goto("/cfa-home");
    const deckId = await cfaDeckId(page);

    await page.goto(`/cfa-deadline/${deckId}`);
    await page.waitForLoadState("networkidle");

    // Brand lockup + heading (proves the page chrome rendered).
    await expect(page.locator(".cfa-page-heading__title")).toHaveText("Deadline planner");
    await expect(page.locator(".cfa-eyebrow")).toHaveText("Peak on exam day");

    // The exam-date picker row (input + set-date pill).
    await expect(page.locator("#cfa-exam-date")).toBeVisible();
    await expect(page.locator(".cfa-deadline__set")).toHaveText("Set exam date");

    // The ranked table: at least one row, bound to real backend data (a freshly
    // seeded CFA deck has new cards, which deadline_retention_with_new ranks so a
    // fresh deck is never a dead-end).
    const table = page.locator(".cfa-table");
    await expect(table).toBeVisible();
    await expect(page.locator(".cfa-deadline__recall").first()).toBeVisible();
    // A never-studied (NEW) card has no memory state, so it renders a calm "New"
    // (muted grey) rather than an alarming warn-orange "0.0%" — the Pass-2 fix.
    // The recall column must NOT be a wall of warn-orange "0.0%".
    await expect(page.locator(".cfa-deadline__recall.is-new").first()).toBeVisible();
    await expect(page.locator(".cfa-deadline__recall.is-warn")).toHaveCount(0);
    // A calm hint explains the "New" rows (all cards new on a fresh deck).
    await expect(page.getByText(/Every card here is new/)).toBeVisible();

    await page.screenshot({
        path: path.join(OUT, "03-cfa-deadline-ranked.png"),
        fullPage: true,
    });
});

test("Deadline planner shows an honest empty state for a deck with no due cards", async ({ page }) => {
    // Default deck (id 1) has no CFA cards → the honest "No due cards to rank
    // yet." notice + helper caption must render, page chrome intact.
    await page.goto("/cfa-deadline/1");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".cfa-page-heading__title")).toHaveText("Deadline planner");
    await expect(page.getByText("No due cards to rank yet.")).toBeVisible();
    // The table must NOT render in the empty state.
    await expect(page.locator(".cfa-table")).toHaveCount(0);

    await page.screenshot({
        path: path.join(OUT, "04-cfa-deadline-empty.png"),
        fullPage: true,
    });
});
