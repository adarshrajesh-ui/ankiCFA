// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

import type { CfaStudyDeck, CfaStudyPayload } from "../types";
import { masteryPct, syncChipLabel, visibleStudyDecks } from "./study";

const here = dirname(fileURLToPath(import.meta.url));

function deck(over: Partial<CfaStudyDeck>): CfaStudyDeck {
    return {
        id: 1,
        name: "Financial Statement Analysis",
        description: "FRA drills",
        due: 0,
        newCount: 0,
        learn: 0,
        review: 0,
        mastery: null,
        featured: false,
        ...over,
    };
}

function payload(over: Partial<CfaStudyPayload> = {}): CfaStudyPayload {
    return {
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
        totals: { activeDecks: 3, dueToday: 42, newQueued: 10 },
        decks: [],
        selectedDeckId: 1,
        footerText: "Study routes to existing flows.",
        ...over,
    };
}

function componentSource(): string {
    return readFileSync(join(here, "CfaStudyPage.svelte"), "utf8");
}

test("visibleStudyDecks: keeps only three decks and ranks by urgency", () => {
    const rows = visibleStudyDecks([
        deck({ id: 1, name: "Low", due: 2, newCount: 1 }),
        deck({ id: 2, name: "High", due: 10, newCount: 0 }),
        deck({ id: 3, name: "New", due: 0, newCount: 20 }),
        deck({ id: 4, name: "Hidden", due: 0, newCount: 0 }),
    ]);
    expect(rows.map((row) => row.name)).toStrictEqual(["High", "New", "Low"]);
    expect(rows[0].featured).toBe(true);
    expect(rows[1].featured).toBe(false);
});

test("masteryPct: abstaining mastery stays visually honest", () => {
    expect(masteryPct(deck({ mastery: null }))).toBe("—");
    expect(masteryPct(deck({ mastery: 0.735 }))).toBe("74%");
});

test("syncChipLabel: mirrors frozen synced and connect states", () => {
    expect(syncChipLabel(payload())).toBe("Synced 14:32");
    expect(syncChipLabel(payload({ sync: { ...payload().sync, connected: false } }))).toBe("Connect & Sync");
});

test("Study page keeps frozen liquid-glass deck workspace selectors", () => {
    const src = componentSource();
    expect(src).toContain("Study - Deck Command Center");
    expect(src).toContain("Your CFA decks, ready to build and study.");
    expect(src).toContain('class="cfa-study__appbar"');
    expect(src).toContain('class="cfa-study__hero"');
    expect(src).toContain('class="cfa-study__workspace-grid"');
    expect(src).toContain('class="cfa-study__deck-grid"');
    expect(src).toContain('class="cfa-study__add-card-panel"');
    expect(src).toContain("Top 3 by urgency");
});

test("Study page routes controls to existing bridge flows", () => {
    const src = componentSource();
    expect(src).toContain('go("create")');
    expect(src).toContain('go("create-cfa")');
    expect(src).toContain('go("import")');
    expect(src).toContain('deckCmd("study", deck)');
    expect(src).toContain('deckCmd("add", deck)');
    expect(src).toContain('go("cfa:conceptmap")');
});
