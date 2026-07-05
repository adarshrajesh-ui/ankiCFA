// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

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

test("D-P4-15: graphs screen adopts the CFA design system", () => {
    const src = graphsSource();
    // The CFA theme (fonts + :root tokens) and the brand Eyebrow are pulled in…
    expect(src).toContain('import "$lib/cfa/theme.scss";');
    expect(src).toContain('import Eyebrow from "$lib/cfa/Eyebrow.svelte";');
    // …a brand eyebrow introduces the statistics surface…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*ankiCFA · Level II · Study statistics/);
    // …and the content opts into the CFA page base.
    expect(src).toMatch(/class="cfa-graphs cfa-app"/);
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
