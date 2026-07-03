// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Standalone copy of the ONE-PASSAGE multi-span tokenization + grading logic used by the passage
// card template. The region between the CFA-SPAN-SHARED markers below is mirrored BYTE-FOR-BYTE
// (ignoring leading indentation) in cfa/ethics_pairs/templates/passage_front.html; test_passages.py
// asserts they match and that this logic agrees with the Python implementation in ethics_scoring.py.
// Only this file adds the module.exports at the end so Node can import it for the cross-language test.

// === CFA-SPAN-SHARED-START ===
// Mirrored byte-for-byte (ignoring indentation) in cfa/ethics_pairs/tests/js/passage_logic.js and
// (in Python) in ethics_scoring.py. tests/test_passages.py enforces the copy match and the
// Python<->JS behavioural agreement. Do NOT edit one copy without the others.
var CFA_SPAN_CAP_SLACK = 4;
var CFA_STRIP_CHARS = ".,;:!?\"'()[]{}…-–—‘’“”";
function cfaStripToken(tok) {
  var s = 0, e = tok.length;
  while (s < e && CFA_STRIP_CHARS.indexOf(tok.charAt(s)) !== -1) s++;
  while (e > s && CFA_STRIP_CHARS.indexOf(tok.charAt(e - 1)) !== -1) e--;
  return tok.slice(s, e).toLowerCase();
}
function cfaTokenize(text) {
  if (text == null) return [];
  var t = String(text).replace(/^\s+|\s+$/g, "");
  if (t === "") return [];
  return t.split(/\s+/);
}
function cfaNormalizedTokens(text) {
  var toks = cfaTokenize(text), out = [];
  for (var i = 0; i < toks.length; i++) out.push(cfaStripToken(toks[i]));
  return out;
}
function cfaFindGold(passage, gold) {
  var v = cfaNormalizedTokens(passage), g = cfaNormalizedTokens(gold);
  if (g.length === 0) return [];
  for (var start = 0; start + g.length <= v.length; start++) {
    var ok = true;
    for (var k = 0; k < g.length; k++) {
      if (v[start + k] !== g[k]) { ok = false; break; }
    }
    if (ok) {
      var idx = [];
      for (var j = 0; j < g.length; j++) idx.push(start + j);
      return idx;
    }
  }
  return [];
}
function cfaFindGoldSpans(passage, phrases) {
  var out = [];
  for (var i = 0; i < phrases.length; i++) out.push(cfaFindGold(passage, phrases[i]));
  return out;
}
function cfaSpanCap(goldTokenCount, nSpans) {
  return goldTokenCount + CFA_SPAN_CAP_SLACK * Math.max(1, nSpans);
}
function cfaGradeSpans(selectionIndices, goldSpans, cap) {
  var sel = {}, selCount = 0, i;
  for (i = 0; i < selectionIndices.length; i++) {
    if (!sel[selectionIndices[i]]) { sel[selectionIndices[i]] = true; selCount++; }
  }
  var perSpan = [], allGold = {}, allGoldCount = 0, found = 0;
  for (var s = 0; s < goldSpans.length; s++) {
    var span = goldSpans[s], covered = span.length > 0, k;
    for (k = 0; k < span.length; k++) {
      if (!allGold[span[k]]) { allGold[span[k]] = true; allGoldCount++; }
      if (!sel[span[k]]) covered = false;
    }
    perSpan.push(covered);
    if (covered) found++;
  }
  var total = goldSpans.length;
  if (cap == null) cap = cfaSpanCap(allGoldCount, total);
  var widthOk = selCount <= cap;
  var grade;
  if (selCount === 0 || found === 0) grade = "wrong";
  else if (found < total) grade = "partial";
  else if (!widthOk) grade = "somewhat";
  else grade = "correct";
  return { grade: grade, found: found, total: total, per_span: perSpan, width_ok: widthOk, cap: cap };
}
// --- Item 2: deterministic partial-credit tolerance (mobile has no network, so no F2 AI here) ---
// The strict cfaGradeSpans above only credits a gold span when EVERY one of its tokens is selected,
// so a materially-correct highlight with different boundaries (e.g. "unreleased quarterly earnings"
// for the gold "exact unreleased quarterly earnings figure") scored a flat "wrong". cfaSpanTier adds
// deterministic tolerance: a span is "full" when every gold token is covered (superset ok), "near"
// when the selection overlaps at least half the gold tokens (right idea, boundaries off), else
// "none". cfaGradeSpansTolerant then awards partial-credit tiers instead of harsh binary matching,
// mirroring the desktop F2 grader's tolerance while staying fully offline + deterministic.
function cfaSpanTier(sel, span) {
  if (span.length === 0) return "none";
  var inter = 0, k;
  for (k = 0; k < span.length; k++) if (sel[span[k]]) inter++;
  if (inter === span.length) return "full";
  if (inter > 0 && inter * 2 >= span.length) return "near";
  return "none";
}
function cfaGradeSpansTolerant(selectionIndices, goldSpans, cap) {
  var sel = {}, selCount = 0, i;
  for (i = 0; i < selectionIndices.length; i++) {
    if (!sel[selectionIndices[i]]) { sel[selectionIndices[i]] = true; selCount++; }
  }
  var perSpan = [], allGold = {}, allGoldCount = 0, full = 0, near = 0;
  for (var s = 0; s < goldSpans.length; s++) {
    var span = goldSpans[s], k;
    for (k = 0; k < span.length; k++) {
      if (!allGold[span[k]]) { allGold[span[k]] = true; allGoldCount++; }
    }
    var tier = cfaSpanTier(sel, span);
    perSpan.push(tier);
    if (tier === "full") full++;
    else if (tier === "near") near++;
  }
  var total = goldSpans.length, matched = full + near;
  if (cap == null) cap = cfaSpanCap(allGoldCount, total);
  var widthOk = selCount <= cap;
  var grade;
  if (selCount === 0 || matched === 0) grade = "wrong";
  else if (matched < total) grade = "partial";
  else if (full === total && widthOk) grade = "correct";
  else grade = "somewhat";
  return { grade: grade, found: full, near: near, matched: matched, total: total, per_span: perSpan, width_ok: widthOk, cap: cap };
}
// === CFA-SPAN-SHARED-END ===

module.exports = {
  CFA_SPAN_CAP_SLACK: CFA_SPAN_CAP_SLACK,
  cfaStripToken: cfaStripToken,
  cfaTokenize: cfaTokenize,
  cfaNormalizedTokens: cfaNormalizedTokens,
  cfaFindGold: cfaFindGold,
  cfaFindGoldSpans: cfaFindGoldSpans,
  cfaSpanCap: cfaSpanCap,
  cfaGradeSpans: cfaGradeSpans,
  cfaSpanTier: cfaSpanTier,
  cfaGradeSpansTolerant: cfaGradeSpansTolerant,
};
