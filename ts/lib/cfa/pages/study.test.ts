// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

import type { CfaStudyDeck, CfaStudyPayload } from "../types";
import { masteryPct, STUDY_NAV, syncChipLabel, TOP_URGENT_DECK_COUNT, visibleStudyDecks } from "./study";

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
            resultLabel: "Synced as learner@example.com (AnkiWeb).",
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

function productNavSource(): string {
    return readFileSync(join(here, "../ProductShellNav.svelte"), "utf8");
}

test("visibleStudyDecks: ranks by urgency without hiding lower-priority decks", () => {
    const rows = visibleStudyDecks([
        deck({ id: 1, name: "Low", due: 2, newCount: 1 }),
        deck({ id: 2, name: "High", due: 10, newCount: 0 }),
        deck({ id: 3, name: "New", due: 0, newCount: 20 }),
        deck({ id: 4, name: "Alpha Rest", due: 0, newCount: 0 }),
        deck({ id: 5, name: "Beta Rest", due: 0, newCount: 0 }),
    ]);
    expect(rows.map((row) => row.name)).toStrictEqual([
        "High",
        "New",
        "Low",
        "Alpha Rest",
        "Beta Rest",
    ]);
    expect(rows).toHaveLength(5);
    expect(rows.filter((row) => row.featured)).toHaveLength(TOP_URGENT_DECK_COUNT);
    expect(rows.slice(0, TOP_URGENT_DECK_COUNT).every((row) => row.featured)).toBe(true);
    expect(rows.slice(TOP_URGENT_DECK_COUNT).some((row) => row.featured)).toBe(false);
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
    const nav = productNavSource();
    expect(src).toContain("Study - Deck Command Center");
    expect(src).toContain("Your CFA decks, ready to build and study.");
    expect(src).toContain("ProductShellNav");
    expect(src).toContain("active=\"study\"");
    expect(src).not.toContain("surfaceClass=");
    expect(nav).toContain("class=\"cfa-product-nav\"");
    expect(src).toContain("class=\"cfa-study__hero\"");
    expect(src).toContain("class=\"cfa-study__workspace-grid\"");
    expect(src).toContain("class=\"cfa-study__deck-list\"");
    expect(src).toContain("class=\"cfa-study__deck-priority\"");
    expect(src).toContain("class=\"cfa-study__deck-scroll\"");
    expect(src).toContain("cfa-study__deck-grid");
    expect(src).toContain("class=\"cfa-study__add-card-panel\"");
    expect(src).toContain("Top 3 by urgency");
    expect(src).toContain("More decks");
});

test("Study page routes controls to existing bridge flows", () => {
    const src = componentSource();
    expect(src).toContain("go(\"create-cfa\")");
    expect(src).toContain("go(\"import\")");
    expect(src).toContain("deckCmd(\"study\", deck)");
    expect(src).toContain("deckCmd(\"add\", deck)");
    expect(src).toContain("go(\"cfa:conceptmap\")");
});

test("Study add/import copy documents the native phone hand-off", () => {
    const src = componentSource();
    expect(src).toContain("class=\"cfa-study__native-note\"");
    expect(src).toContain("Phone hand-off: Add and Import use Anki's native screens");
    expect(src).toContain("Basic note type");
});

test("Study page has one clear CFA/Ethics creation action", () => {
    const src = componentSource();
    expect(src).toContain("Create CFA/Ethics study deck");
    expect(src).not.toContain("Create new deck");
    expect(src).not.toContain("Create CFA deck");
    expect(src.match(/go\("create-cfa"\)/g)).toHaveLength(1);
});

test("Study deck cards stack as full-width horizontal rows", () => {
    const src = componentSource();
    expect(src).toMatch(/&__deck-grid\s*\{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/);
    expect(src).toMatch(/&__deck-card\s*\{[\s\S]*?grid-template-areas:[\s\S]*?"summary stats actions"/);
    expect(src).not.toContain("repeat(auto-fit, minmax(220px, 1fr))");
});

test("Study deck list keeps top urgent decks above scrollable rest", () => {
    const src = componentSource();
    expect(src).toContain("{#each topUrgencyDecks as deck}");
    expect(src).toContain("aria-label=\"More CFA decks\"");
    expect(src).toContain("{#each remainingDecks as deck}");
    expect(src).toMatch(/&__workspace-grid\s*\{[\s\S]*?align-items: start;/);
    expect(src).toMatch(/&__deck-scroll\s*\{[\s\S]*?max-height: clamp\(320px, calc\(100vh - 420px\), 560px\);/);
    expect(src).toMatch(/&__deck-scroll\s*\{[\s\S]*?overflow-y: auto;/);
});

test("Study desktop workspace stacks before deck rows overflow", () => {
    const src = componentSource();
    const start = src.indexOf("@media (max-width: 1120px)");
    const end = src.indexOf("@media (max-width: 980px)", start);
    const medium = src.slice(start, end);

    expect(medium).toMatch(/&__workspace-grid\s*\{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/);
    expect(medium).toMatch(/&__add-card-panel\s*\{[\s\S]*?position: static;/);
    expect(medium).not.toMatch(/&__metric-row\s*\{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/);
});

test("Study page has phone-safe mobile workspace rules", () => {
    const src = componentSource();
    const nav = productNavSource();
    expect(src).toMatch(/@media \(max-width: 720px\)\s*\{[\s\S]*?&__page\s*\{[\s\S]*?padding: 14px 12px 64px;/);
    expect(src).toMatch(/&__hero-actions\s*\{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/);
    expect(src).toMatch(/&__deck-card\s*\{[\s\S]*?grid-template-areas:[\s\S]*?"summary"[\s\S]*?"actions";/);
    expect(src).toMatch(/&__deck-scroll\s*\{[\s\S]*?max-height: none;[\s\S]*?overflow-y: visible;/);
    expect(nav).toMatch(/\.cfa-product-nav__tabs\s*\{[\s\S]*?overflow-x: auto;/);
    expect(src).toMatch(/&__quick-add-row\s*\{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/);
});

test("Study page uses visible reduced product nav on desktop", () => {
    const src = componentSource();
    const nav = productNavSource();
    expect(STUDY_NAV.map((item) => item.cmd)).toStrictEqual([
        "cfa:home",
        "cfa:study",
        "cfa:conceptmap",
        "cfa:readiness",
        "cfa:progress",
        "cfa:sync",
    ]);
    expect(src).not.toContain("Desktop shell uses the native Qt toolbar");
    expect(nav).toMatch(/\.cfa-product-nav__tabs\s*\{[\s\S]*?display: flex;/);
});
