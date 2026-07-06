// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));

// --- Phase B regression guard (D-P4-19) ---------------------------------
// The Change-notetype dialog (Browse → Notes → Change Notetype) — where a CFA
// candidate would remap a deck onto the branded "CFA Knowledge" notetype — was
// a 100%-stock-Anki SvelteKit surface: a stock-blue Save button, blue focus
// rings, blue links, and a blue selected notetype row. For the objective's "no
// visibly un-themed stock-Anki screens remain" bar it must read as the CFA
// design system. The retone works by overriding the stock-blue design-token
// CSS vars in-scope, so every descendant control adopts CFA navy/accent at
// once. Lock it in source.
function changeNotetypeSource(): string {
    return readFileSync(join(here, "ChangeNotetypePage.svelte"), "utf8");
}

test("D-P4-19: change-notetype adopts the CFA design system", () => {
    const src = changeNotetypeSource();
    // The CFA theme (fonts + :root tokens) and brand Eyebrow are pulled in…
    expect(src).toContain("import \"$lib/cfa/theme.scss\";");
    expect(src).toContain("import Eyebrow from \"$lib/cfa/Eyebrow.svelte\";");
    // …a brand eyebrow introduces the surface…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*ankiCFA · Level II · Change notetype/);
    // …and the content opts into the CFA page base, light-mode gated.
    expect(src).toMatch(/class="cfa-changenote cfa-app"/);
    expect(src).toContain("class:is-light={!$pageTheme.isDark}");
});

test("D-P4-19: stock-blue interactive tokens are retoned to CFA, scoped + light-only", () => {
    const src = changeNotetypeSource();
    expect(src).toMatch(/@use "\.\.\/\.\.\/lib\/cfa\/tokens" as cfa;/);
    // The stock-Anki blue interactive vars are all overridden in-scope…
    expect(src).toMatch(/--button-primary-bg: #\{cfa\.\$cfa-primary\};/);
    expect(src).toMatch(/--border-focus: #\{cfa\.\$cfa-accent\};/);
    expect(src).toMatch(/--fg-link: #\{cfa\.\$cfa-accent\};/);
    expect(src).toMatch(/--selected-bg: #\{cfa\.\$cfa-accent-soft\};/);
    // …only under the light-mode scope, so the dark theme keeps its own tokens
    // and the overrides never leak to other TitledContainer users.
    expect(src).toMatch(/\.cfa-changenote\.is-light \{/);
    // Serif-navy section titles ("Fields"/"Templates") are scoped to this page.
    expect(src).toMatch(/\.cfa-changenote\.is-light :global\(\.container\.light h1\)/);
});

test("D-P4-19: functional change-notetype behaviour is preserved", () => {
    const src = changeNotetypeSource();
    // Theming is presentation-only — the selector, both mappers, the sticky
    // headers, and the cloze fallback must all be untouched.
    expect(src).toContain("<NotetypeSelector {state} />");
    expect(src).toContain("<Mapper {state} ctx={MapContext.Field} />");
    expect(src).toContain("<Mapper {state} ctx={MapContext.Template} />");
    expect(src).toContain("<StickyHeader {state} ctx={MapContext.Field} />");
    expect(src).toContain("{@html renderMarkdown(tr.changeNotetypeToFromCloze())}");
});
