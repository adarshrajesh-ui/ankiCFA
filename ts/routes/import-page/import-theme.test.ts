// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));

// --- Phase B regression guard (D-P4-20) ---------------------------------
// The Import shell (ImportPage.svelte) is the shared shell for BOTH import
// flows — Anki-package import (where a CFA candidate imports the shared CFA
// deck .apkg during onboarding) and CSV import — as well as the post-import
// results log. It was a 100%-stock-Anki SvelteKit surface: a stock-blue
// primary Import button, blue focus rings, blue links, and blue selected rows.
// For the objective's "no visibly un-themed stock-Anki screens remain" bar it
// must read as the CFA design system. Theming this one shared component retones
// every import surface at once, via in-scope stock-blue design-token overrides.
// Lock it in source.
function importPageSource(): string {
    return readFileSync(join(here, "ImportPage.svelte"), "utf8");
}

test("D-P4-20: the import shell adopts the CFA design system", () => {
    const src = importPageSource();
    // The CFA theme (fonts + :root tokens) and brand Eyebrow are pulled in…
    expect(src).toContain("import \"$lib/cfa/theme.scss\";");
    expect(src).toContain("import Eyebrow from \"$lib/cfa/Eyebrow.svelte\";");
    // …a brand eyebrow introduces the surface…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*EthosPrep · Level II · Import/);
    // …and the whole shell opts into the CFA page base, light-mode gated so
    // every branch (options / progress / results / error) is wrapped.
    expect(src).toMatch(/class="cfa-import cfa-app"/);
    expect(src).toContain("class:is-light={!$pageTheme.isDark}");
});

test("D-P4-20: stock-blue interactive tokens are retoned to CFA, scoped + light-only", () => {
    const src = importPageSource();
    expect(src).toMatch(/@use "\.\.\/\.\.\/lib\/cfa\/tokens" as cfa;/);
    // The stock-Anki blue interactive vars are all overridden in-scope, so the
    // primary Import button, focus rings, links, and selected rows read as CFA…
    expect(src).toMatch(/--button-primary-bg: #\{cfa\.\$cfa-primary\};/);
    expect(src).toMatch(/--border-focus: #\{cfa\.\$cfa-accent\};/);
    expect(src).toMatch(/--fg-link: #\{cfa\.\$cfa-accent\};/);
    expect(src).toMatch(/--selected-bg: #\{cfa\.\$cfa-accent-soft\};/);
    // …only under the light-mode scope, so the dark theme keeps its own tokens
    // and the overrides never leak to other TitledContainer users.
    expect(src).toMatch(/\.cfa-import\.is-light \{/);
    // Serif-navy section titles ("Import options"/"Overview"/"Details").
    expect(src).toMatch(/\.cfa-import\.is-light :global\(\.container\.light h1\)/);
});

test("D-P4-20: functional import behaviour is preserved", () => {
    const src = importPageSource();
    // Theming is presentation-only — the import lifecycle branches (error page,
    // results log, progress indicator, sticky header + options slot) and the
    // doImport/importDone wiring must all be untouched.
    expect(src).toContain("<ErrorPage {error} />");
    expect(src).toContain("<ImportLogPage response={importResponse} />");
    expect(src).toContain("<BackendProgressIndicator");
    expect(src).toContain("<StickyHeader {path} onImport={() => (importing = true)} />");
    expect(src).toContain("<slot />");
    expect(src).toContain("await importer.doImport()");
    expect(src).toContain("await importDone({});");
});
