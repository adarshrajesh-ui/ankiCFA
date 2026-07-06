// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

import { productNavItems } from "../../lib/cfa/productNav";

const here = dirname(fileURLToPath(import.meta.url));

// --- Phase B regression guard (D-P4-15) ---------------------------------
// The statistics screen (GraphsPage.svelte, opened from the Stats action) was
// the largest remaining 100%-stock-Anki SvelteKit surface: bare canvas, stock
// TitledContainer card titles, a stock `--canvas`/`--border` range selector. For
// a CFA exam-prep product "how am I tracking" is core, so its chrome must read
// as the CFA design system — the objective's "no visibly un-themed stock-Anki
// screens remain" bar. Lock the theming in the source so it can't regress.
function graphsSource(): string {
    return readFileSync(join(here, "GraphsPage.svelte"), "utf8");
}

function productShellNavSource(): string {
    return readFileSync(join(here, "../../lib/cfa/ProductShellNav.svelte"), "utf8");
}

test("D-P4-15: graphs screen adopts the CFA design system", () => {
    const src = graphsSource();
    // The CFA theme (fonts + :root tokens) and the brand Eyebrow are pulled in…
    expect(src).toContain("import \"$lib/cfa/theme.scss\";");
    expect(src).toContain("import Eyebrow from \"$lib/cfa/Eyebrow.svelte\";");
    // …a brand eyebrow + command-center hero introduce the statistics surface…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*ankiCFA · Level II · Study statistics/);
    expect(src).toContain("Progress Command Center");
    expect(src).toContain("Click any chart segment to drill into");
    // …and the content opts into the CFA page base.
    expect(src).toMatch(/class="cfa-graphs cfa-app"/);
});

test("D-P4-15: graphs screen has the in-page reduced product nav", () => {
    const src = graphsSource();
    expect(src).toContain("ProductShellNav");
    expect(src).toContain("active=\"progress\"");
    expect(src).not.toContain("surfaceClass=");
    expect(src).toContain("ariaLabel=\"CFA sections\"");
    expect(src).toContain("on:navigate={(event) => go(event.detail)}");
    expect(productNavItems("progress").map((item) => item.cmd)).toStrictEqual([
        "cfa:home",
        "cfa:study",
        "cfa:conceptmap",
        "cfa:readiness",
        "cfa:progress",
        "cfa:sync",
    ]);
});

test("D-P4-15: graphs chrome uses CFA tokens, scoped to this surface", () => {
    const src = graphsSource();
    expect(src).toMatch(/@use "\.\.\/\.\.\/lib\/cfa\/tokens" as cfa;/);
    // Serif-navy card titles + CFA hairline card edges…
    expect(src).toMatch(/\.cfa-graphs :global\(\.container\.light h1\)/);
    expect(src).toMatch(/font-family: cfa\.\$cfa-font-heading;/); // serif titles
    expect(src).toMatch(/color: cfa\.\$cfa-ink;/); // brand navy
    // …a CFA-toned range selector with a warm-accent control tint.
    expect(src).toMatch(/\.cfa-graphs :global\(\.range-box\)/);
    expect(src).toMatch(/accent-color: cfa\.\$cfa-accent;/);
    // …and glass-panel treatment makes the formerly stock page feel native to
    // the current premium CFA shell without changing graph internals.
    expect(src).toContain("backdrop-filter: blur");
    expect(src).toContain("box-shadow: 0 22px 60px");
    expect(src).toContain("cfa-progress-hero");
    // Retones are scoped under .cfa-graphs so shared components elsewhere are
    // never restyled (no bare global TitledContainer/InputBox override).
    expect(src).not.toMatch(/^\s*:global\(\.container\)/m);
});

test("D-P4-15: functional graphs behaviour is preserved", () => {
    const src = graphsSource();
    // The theming is presentation-only — the data query + chart rendering that
    // drive the screen must be untouched.
    expect(src).toContain("WithGraphData");
    expect(src).toContain("browserSearch");
    expect(src).toContain("bridgeCommand(`browserSearch:");
    expect(src).toContain("nightMode={$pageTheme.isDark}");
    expect(src).toContain("each graphs as graph");
});

test("D-P4-15: progress graph shell has phone-safe layout affordances", () => {
    const src = graphsSource();
    const nav = productShellNavSource();
    expect(src).toMatch(/@media only screen and \(max-width: 600px\)/);
    expect(src).toContain("cfa-progress-appbar-wrap");
    expect(src).toContain("ProductShellNav");
    expect(src).toMatch(
        /\.cfa-progress-appbar-wrap,\s*\n\s*\.cfa-graphs-shell\s*\{[\s\S]*?width: min\(100% - 1rem, 1320px\);/,
    );
    expect(src).toMatch(/\.cfa-graphs :global\(\.range-box\)\s*\{[\s\S]*?box-sizing: border-box;/);
    expect(src).toMatch(/grid-template-columns: 1fr;/);
    expect(src).toMatch(
        /\.cfa-graphs :global\(\.range-box input\[type="text"\]\)\s*\{[\s\S]*?width: min\(100%, 18rem\);/,
    );
    expect(nav).toMatch(/@media \(max-width: 720px\)/);
    expect(nav).toMatch(/\.cfa-product-nav__tabs\s*\{[\s\S]*?overflow-x: auto;/);
    expect(nav).toMatch(/\.cfa-product-nav__tabs button\s*\{[\s\S]*?min-height: 44px;/);
});
