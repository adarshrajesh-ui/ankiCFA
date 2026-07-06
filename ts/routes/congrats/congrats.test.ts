// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));

// --- Phase B regression guard (D-P4-11) ---------------------------------
// The study-session "Congratulations — finished" screen (CongratsPage.svelte,
// shown at the end of every completed study session) shipped as stock Anki: a
// plain <h1>, stock `--fg-link` links, a `--border` description box on the bare
// canvas. It is the reward surface a learner sees after every session, so it
// must read as a purpose-built CFA screen — the objective's "no visibly
// un-themed stock-Anki screens remain" bar. Lock the CFA theming in the source
// so it can't silently regress to the stock look.
function congratsSource(): string {
    return readFileSync(join(here, "CongratsPage.svelte"), "utf8");
}

test("D-P4-11: congrats screen adopts the CFA design system", () => {
    const src = congratsSource();
    // The CFA theme (fonts + :root tokens) and the brand Eyebrow are pulled in…
    expect(src).toContain("import \"$lib/cfa/theme.scss\";");
    expect(src).toContain("import Eyebrow from \"$lib/cfa/Eyebrow.svelte\";");
    // …a brand eyebrow introduces the session-complete heading…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*ankiCFA · Level II · Session complete/);
    // …and the container opts into the CFA page base.
    expect(src).toMatch(/class="congrats cfa-app"/);
});

test("D-P4-11: congrats styling uses CFA tokens, not stock Anki vars", () => {
    const src = congratsSource();
    // The stock Anki style hooks must be gone from the scoped styles…
    expect(src).not.toContain("var(--fg-link)");
    expect(src).not.toContain("border: 1px solid var(--border)");
    // …replaced by the CFA token module + brand serif heading + accent links.
    expect(src).toMatch(/@use "\.\.\/\.\.\/lib\/cfa\/tokens" as cfa;/);
    expect(src).toMatch(/font-family: cfa\.\$cfa-font-heading;/); // serif h1
    expect(src).toMatch(/color: cfa\.\$cfa-accent;/); // accent links
    expect(src).toMatch(/border: 1px solid cfa\.\$cfa-line;/); // CFA hairline
});

test("D-P4-11: functional congrats behaviour is preserved", () => {
    const src = congratsSource();
    // The theming is presentation-only — the scheduling logic + bridge links
    // that drive the screen must be untouched.
    expect(src).toContain("congratsInfo");
    expect(src).toContain("buildNextLearnMsg");
    expect(src).toContain("bridgeLink(\"unbury\"");
    expect(src).toContain("bridgeLink(\"customStudy\"");
    expect(src).toContain("info.deckDescription");
});
