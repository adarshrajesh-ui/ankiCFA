// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Standalone copy of the highlight tokenization + grading logic used by the card template. The
// region between the CFA-HIGHLIGHT-SHARED markers below is mirrored BYTE-FOR-BYTE (ignoring leading
// indentation) in cfa/ethics_pairs/templates/front.html; test_highlight.py asserts they match and
// that this logic agrees with the Python implementation in ethics_scoring.py. Only this file adds
// the module.exports at the end so Node can import it for the cross-language test.

// === CFA-HIGHLIGHT-SHARED-START ===
// Mirrored byte-for-byte in cfa/ethics_pairs/tests/js/highlight_logic.js and (in Python) in
// ethics_scoring.py. test_highlight.py enforces the JS<->JS copy match and the Python<->JS
// behavioural agreement. Do NOT edit one copy without the others.
var CFA_HIGHLIGHT_CAP_SLACK = 5;
var CFA_STRIP_CHARS = ".,;:!?\"'()[]{}\u2026-\u2013\u2014\u2018\u2019\u201c\u201d";
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
function cfaFindGold(vignette, gold) {
  var v = cfaNormalizedTokens(vignette), g = cfaNormalizedTokens(gold);
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
function cfaDefaultCap(goldLen) { return goldLen + CFA_HIGHLIGHT_CAP_SLACK; }
function cfaGradeHighlight(selectionIndices, goldIndices, cap) {
  if (cap == null) cap = cfaDefaultCap(goldIndices.length);
  var sel = {}, selCount = 0, i;
  for (i = 0; i < selectionIndices.length; i++) {
    if (!sel[selectionIndices[i]]) { sel[selectionIndices[i]] = true; selCount++; }
  }
  if (selCount === 0) return "wrong";
  for (i = 0; i < goldIndices.length; i++) {
    if (!sel[goldIndices[i]]) return "wrong";
  }
  return selCount <= cap ? "correct" : "somewhat";
}
// === CFA-HIGHLIGHT-SHARED-END ===

module.exports = {
  CFA_HIGHLIGHT_CAP_SLACK: CFA_HIGHLIGHT_CAP_SLACK,
  cfaStripToken: cfaStripToken,
  cfaTokenize: cfaTokenize,
  cfaNormalizedTokens: cfaNormalizedTokens,
  cfaFindGold: cfaFindGold,
  cfaDefaultCap: cfaDefaultCap,
  cfaGradeHighlight: cfaGradeHighlight,
};
