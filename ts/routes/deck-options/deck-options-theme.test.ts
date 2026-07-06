// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));

// --- Phase B regression guard (D-P4-18) ---------------------------------
// The deck-options (Study settings) dialog — the scheduling/FSRS config a
// sophisticated CFA candidate opens to tune their daily load — was a 100%-stock
// -Anki SvelteKit surface: a stock-blue Save button, blue focus rings, blue
// links, and blue selected rows. For the objective's "no visibly un-themed
// stock-Anki screens remain" bar it must read as the CFA design system. The
// retone works by overriding the stock-blue design-token CSS vars in-scope, so
// every descendant control adopts CFA navy/accent at once. Lock it in source.
function deckOptsSource(): string {
    return readFileSync(join(here, "DeckOptionsPage.svelte"), "utf8");
}

test("D-P4-18: deck-options adopts the CFA design system", () => {
    const src = deckOptsSource();
    // The CFA theme (fonts + :root tokens) and brand Eyebrow are pulled in…
    expect(src).toContain("import \"$lib/cfa/theme.scss\";");
    expect(src).toContain("import Eyebrow from \"$lib/cfa/Eyebrow.svelte\";");
    // …a brand eyebrow introduces the settings surface…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*ankiCFA · Level II · Study settings/);
    // …and the content opts into the CFA page base, light-mode gated.
    expect(src).toMatch(/class="cfa-deckopts cfa-app"/);
    expect(src).toContain("class:is-light={!$pageTheme.isDark}");
});

test("D-P4-18: stock-blue interactive tokens are retoned to CFA, scoped + light-only", () => {
    const src = deckOptsSource();
    expect(src).toMatch(/@use "\.\.\/\.\.\/lib\/cfa\/tokens" as cfa;/);
    // The stock-Anki blue interactive vars are all overridden in-scope…
    expect(src).toMatch(/--button-primary-bg: #\{cfa\.\$cfa-primary\};/);
    expect(src).toMatch(/--border-focus: #\{cfa\.\$cfa-accent\};/);
    expect(src).toMatch(/--fg-link: #\{cfa\.\$cfa-accent\};/);
    expect(src).toMatch(/--accent-card: #\{cfa\.\$cfa-primary\};/);
    expect(src).toMatch(/--selected-bg: #\{cfa\.\$cfa-accent-soft\};/);
    // …only under the light-mode scope, so the dark theme keeps its own tokens
    // and the overrides never leak to other TitledContainer/InputBox users.
    expect(src).toMatch(/\.cfa-deckopts\.is-light \{/);
});

test("D-P4-18: functional deck-options behaviour is preserved", () => {
    const src = deckOptsSource();
    // Theming is presentation-only — the config selector, every option section,
    // the preset-change wiring, and the addon api exports must be untouched.
    expect(src).toContain("<ConfigSelector {state} on:presetchange={onPresetChange} />");
    expect(src).toContain("addSvelteAddon");
    expect(src).toContain("addHtmlAddon");
    expect(src).toContain("bind:this={dailyLimitsComponent}");
    expect(src).toContain("bind:this={fsrsOptionsOuterComponent}");
    expect(src).toContain("<FsrsOptionsOuter");
});
