// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));

// --- Phase B regression guard (D-P4-17) ---------------------------------
// The Card Info screen (CardInfo.svelte, opened from the reviewer "More → Card
// Info" and the Browser sidebar) was a 100%-stock-Anki surface: a bare white
// page, an unstyled key/value stats table, and stock traffic-light revlog
// colours. For a CFA exam-prep product a card's review history is core, so its
// chrome must read as the CFA design system — the objective's "no visibly
// un-themed stock-Anki screens remain" bar. Lock the theming in the source.
function cardInfoSource(): string {
    return readFileSync(join(here, "CardInfo.svelte"), "utf8");
}

test("D-P4-17: card info screen adopts the CFA design system", () => {
    const src = cardInfoSource();
    // The CFA theme (fonts + :root tokens) and the brand Eyebrow are pulled in…
    expect(src).toContain("import \"$lib/cfa/theme.scss\";");
    expect(src).toContain("import Eyebrow from \"$lib/cfa/Eyebrow.svelte\";");
    // …a brand eyebrow introduces the surface…
    expect(src).toMatch(/<Eyebrow[^>]*>[^<]*ankiCFA · Level II · Card details/);
    // …and the content opts into the CFA page base.
    expect(src).toMatch(/class="cfa-cardinfo cfa-app"/);
});

test("D-P4-17: card info chrome uses CFA tokens, scoped to this surface", () => {
    const src = cardInfoSource();
    expect(src).toMatch(/@use "\.\.\/\.\.\/lib\/cfa\/tokens" as cfa;/);
    // Serif-navy stat labels + CFA hairline row rules…
    expect(src).toMatch(/\.cfa-cardinfo :global\(\.stats-table th\)/);
    expect(src).toMatch(/font-family: cfa\.\$cfa-font-heading;/); // serif labels
    expect(src).toMatch(/color: cfa\.\$cfa-ink;/); // brand navy
    // …and the stock traffic-light revlog colours are retoned to CFA tones.
    expect(src).toMatch(/\.cfa-cardinfo :global\(\.revlog-learn\)/);
    expect(src).toMatch(/color: cfa\.\$cfa-accent;/);
    expect(src).toMatch(/color: cfa\.\$cfa-fail;/);
    // The light page tint is guarded to light mode so dark theme keeps its own
    // tokens (learning from the reviewer-chrome iteration).
    expect(src).toMatch(/:global\(body:not\(\.nightMode\)\) \.cfa-cardinfo/);
    // Retones are scoped under .cfa-cardinfo so shared components elsewhere are
    // never restyled (no bare global stats-table override).
    expect(src).not.toMatch(/^\s*:global\(\.stats-table\)/m);
});

test("D-P4-17: functional card info behaviour is preserved", () => {
    const src = cardInfoSource();
    // The theming is presentation-only — the stats query, revlog table, and
    // forgetting-curve chart that drive the screen must be untouched.
    expect(src).toContain("CardStats");
    expect(src).toContain("Revlog");
    expect(src).toContain("ForgettingCurve");
    expect(src).toContain("CardInfoPlaceholder");
    expect(src).toContain("fsrsEnabled");
});
