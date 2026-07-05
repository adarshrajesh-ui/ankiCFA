// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// -----------------------------------------------------------------------------
// Phase B Pass 3 (ruthless) — a SCIENTIFIC WCAG 2.1 contrast audit of the CFA
// web design tokens. Every token that colours READABLE TEXT must clear AA
// (>=4.5:1 for body, >=3:1 for large text) against the backgrounds it can sit
// on; the palette is parsed straight out of `_tokens.scss` so the audit catches
// any future value drift. The audit found `$cfa-faint` (#939597) fails AA for
// text, so it was demoted to DECORATIVE-ONLY and a new AA-safe `$cfa-faint-ink`
// tertiary-text token was introduced (repointed across Caption / StatCard /
// Hero / Home / Readiness). This test locks that conclusion in place.
// -----------------------------------------------------------------------------

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));

/** Parse `$cfa-<name>: #rrggbb;` declarations out of `_tokens.scss`. */
function loadTokens(): Record<string, string> {
    const scss = readFileSync(join(here, "_tokens.scss"), "utf8");
    const tokens: Record<string, string> = {};
    const re = /\$cfa-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\b/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(scss)) !== null) {
        tokens[m[1]] = m[2].toLowerCase();
    }
    return tokens;
}

/** WCAG relative luminance of a #rrggbb colour. */
function luminance(hex: string): number {
    const chan = (v: number): number => {
        const c = v / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b);
}

/** WCAG contrast ratio between two #rrggbb colours (>=1, symmetric). */
function contrast(a: string, b: string): number {
    const la = luminance(a);
    const lb = luminance(b);
    const hi = Math.max(la, lb);
    const lo = Math.min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
}

const AA_BODY = 4.5;
const AA_LARGE = 3.0;
// WCAG 2.1 SC 1.4.11 Non-text Contrast: the visual boundary of an active user
// interface component (button / text input) must reach 3:1 against its adjacent
// colour so the control is perceivable.
const AA_NONTEXT = 3.0;

const T = loadTokens();
// The three light backgrounds a CFA text token can realistically sit on.
const BACKGROUNDS = ["bg", "page", "surface"] as const;

describe("CFA design-token contrast audit (WCAG 2.1 AA)", () => {
    test("the contrast helper matches known reference ratios", () => {
        // Black on white is the canonical 21:1; white on white is 1:1.
        expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 0);
        expect(contrast("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
    });

    // The readable-text ramp: primary (ink), secondary (muted), tertiary
    // (faint-ink). Every one must clear AA BODY on every background.
    for (const name of ["ink", "muted", "faint-ink"]) {
        for (const bg of BACKGROUNDS) {
            test(`text token '${name}' clears AA body on '${bg}'`, () => {
                const ratio = contrast(T[name], T[bg]);
                expect(ratio, `${name} on ${bg} = ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
                    AA_BODY,
                );
            });
        }
    }

    test("the new faint-ink token is the Pass-3 fix (AA body everywhere)", () => {
        // Regression anchor: faint-ink must exist and clear 4.5:1 on the worst
        // (surface) background, or the audit is not actually satisfied.
        expect(T["faint-ink"]).toBeDefined();
        expect(contrast(T["faint-ink"], T["surface"])).toBeGreaterThanOrEqual(AA_BODY);
    });

    test("a clean type hierarchy: ink darker than muted darker than faint-ink", () => {
        // Preserve visual hierarchy — the fix must not flatten all greys to one.
        expect(contrast(T["ink"], T["bg"])).toBeGreaterThan(contrast(T["muted"], T["bg"]));
        expect(contrast(T["muted"], T["bg"])).toBeGreaterThan(
            contrast(T["faint-ink"], T["bg"]),
        );
    });

    test("the semantic triad reads on white (its primary surface)", () => {
        for (const name of ["pass", "fail", "warn"]) {
            const ratio = contrast(T[name], T["bg"]);
            expect(ratio, `${name} on bg = ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
                AA_BODY,
            );
        }
    });

    test("mm-green is AA-safe for small text (its documented role)", () => {
        expect(contrast(T["mm-green"], T["bg"])).toBeGreaterThanOrEqual(AA_BODY);
    });

    test("DOCUMENTS why $cfa-faint is decorative-only (fails AA as text)", () => {
        // This is the finding that motivated the fix: #939597 is below AA body
        // on white and below even the 3:1 large-text floor on the tinted
        // backgrounds — it must never colour readable text.
        expect(contrast(T["faint"], T["bg"])).toBeLessThan(AA_BODY);
        expect(contrast(T["faint"], T["page"])).toBeLessThan(AA_LARGE);
        expect(contrast(T["faint"], T["surface"])).toBeLessThan(AA_LARGE);
    });

    test("REGRESSION GUARD: $cfa-faint never colours text in a component", () => {
        // The decorative token may only appear as scrollbar-color / background /
        // border-*; a `color: cfa.$cfa-faint` (text) usage would re-introduce the
        // failing-contrast defect. faint-ink is the sanctioned text token.
        const files = [
            "Caption.svelte",
            "StatCard.svelte",
            "Hero.svelte",
            "Notice.svelte",
            "DataTable.svelte",
            "pages/CfaHomePage.svelte",
            "pages/CfaReadinessPage.svelte",
            "pages/CfaDeadlinePage.svelte",
        ];
        for (const f of files) {
            const src = readFileSync(join(here, f), "utf8");
            // Match `color: cfa.$cfa-faint;` but NOT `...$cfa-faint-ink;`.
            const bad = /(?<!-)\bcolor:\s*cfa\.\$cfa-faint\s*;/.test(src);
            expect(bad, `${f} colours text with the decorative $cfa-faint`).toBe(false);
        }
    });
});

// -----------------------------------------------------------------------------
// Pass 3 (ruthless) finding #2 — WCAG 2.1 SC 1.4.11 Non-text Contrast. The text
// audit above only checked text-on-background; a premium product also owes every
// user a PERCEIVABLE control boundary. The decorative hairline `$cfa-line`
// (#e7e9ec) is only ~1.24:1 on white, so an interactive control (secondary CTA,
// footer chip, date input) whose ONLY edge is the hairline is effectively
// invisible (white fill on the near-white page). A new AA-safe
// `$cfa-control-border` clears the 3:1 boundary bar; decorative card edges / table
// rules / dividers correctly keep the exempt hairline.
// -----------------------------------------------------------------------------
describe("CFA control-boundary contrast audit (WCAG 2.1 SC 1.4.11)", () => {
    test("DOCUMENTS why $cfa-line fails as a control boundary (< 3:1)", () => {
        // The finding: the hairline is far below the 3:1 a control edge needs on
        // both the white card fill and the page tint it sits against.
        expect(contrast(T["line"], T["bg"])).toBeLessThan(AA_NONTEXT);
        expect(contrast(T["line"], T["page"])).toBeLessThan(AA_NONTEXT);
    });

    test("the new control-border token clears 3:1 on white and the page tint", () => {
        expect(T["control-border"]).toBeDefined();
        expect(
            contrast(T["control-border"], T["bg"]),
            `control-border on bg = ${contrast(T["control-border"], T["bg"]).toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(AA_NONTEXT);
        expect(
            contrast(T["control-border"], T["page"]),
            `control-border on page = ${contrast(T["control-border"], T["page"]).toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(AA_NONTEXT);
    });

    test("control-border stays lighter than muted (an edge, never text)", () => {
        // It must be perceivable as a boundary but not so dark it reads as text /
        // competes with the muted secondary-text token.
        expect(contrast(T["control-border"], T["bg"])).toBeLessThan(
            contrast(T["muted"], T["bg"]),
        );
    });

    test("FIX: every interactive control uses the AA-safe control edge", () => {
        // The three controls whose only boundary is a border must draw it with
        // control-border, not the decorative hairline.
        const cta = readFileSync(join(here, "pages/CfaHomePage.svelte"), "utf8");
        const deadline = readFileSync(join(here, "pages/CfaDeadlinePage.svelte"), "utf8");
        // Home: the secondary CTA + the footer chip (two controls).
        const homeEdges = cta.match(/border:\s*1px solid cfa\.\$cfa-control-border\b/g) ?? [];
        expect(homeEdges.length, "Home CTA + chip both use control-border").toBeGreaterThanOrEqual(
            2,
        );
        // Deadline: the date input.
        expect(/border:\s*1px solid cfa\.\$cfa-control-border\b/.test(deadline)).toBe(true);
    });

    test("REGRESSION GUARD: decorative components keep the exempt hairline", () => {
        // 1.4.11 exempts pure decoration — card edges, table rules and dividers
        // must NOT be darkened to the control edge (that would make the calm
        // finance-education surface heavy). They keep $cfa-line and never adopt
        // control-border.
        const decorative = [
            "Band.svelte",
            "DataTable.svelte",
            "Hero.svelte",
            "StatCard.svelte",
        ];
        for (const f of decorative) {
            const src = readFileSync(join(here, f), "utf8");
            expect(
                /cfa\.\$cfa-control-border\b/.test(src),
                `${f} must keep the decorative $cfa-line, not the control edge`,
            ).toBe(false);
        }
    });
});
