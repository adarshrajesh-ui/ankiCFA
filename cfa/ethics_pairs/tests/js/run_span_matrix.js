// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Cross-language harness for the ONE-PASSAGE multi-span logic: reads a JSON matrix (argv[2]) of
// gold-span-finding and multi-span grading cases, runs the SAME logic the passage card template uses
// (passage_logic.js), and prints the results as JSON on stdout. test_passages.py compares this
// output against the Python implementation to prove they agree.

const fs = require("fs");
const L = require("./passage_logic.js");

const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = { spans: [], grade: [] };

for (const c of input.spans || []) {
  out.spans.push(L.cfaFindGoldSpans(c.passage, c.phrases));
}
for (const c of input.grade || []) {
  // c.cap is null when the default (len(gold) + slack*n_spans) should be used.
  out.grade.push(L.cfaGradeSpans(c.selection, c.gold_spans, c.cap));
}

process.stdout.write(JSON.stringify(out));
