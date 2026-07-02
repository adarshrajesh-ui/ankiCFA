// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Cross-language harness: reads a JSON matrix (argv[2]) of gold-finding and grading cases, runs the
// SAME logic the card template uses (highlight_logic.js), and prints the results as JSON on stdout.
// test_highlight.py compares this output against the Python implementation to prove they agree.

const fs = require("fs");
const L = require("./highlight_logic.js");

const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = { gold: [], grade: [] };

for (const c of input.gold || []) {
  out.gold.push(L.cfaFindGold(c.vignette, c.gold));
}
for (const c of input.grade || []) {
  // c.cap is null when the default (len(gold) + slack) should be used.
  out.grade.push(L.cfaGradeHighlight(c.selection, c.gold, c.cap));
}

process.stdout.write(JSON.stringify(out));
