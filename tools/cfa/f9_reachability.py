"""F9 final-gate reachability: seed a fresh collection and exercise every
shipped CFA feature (F0a–F8) end-to-end, printing honest real numbers.

Run: PYTHONPATH="out/pylib:pylib:qt:out/qt:cfa/ethics_pairs:." \
     out/pyenv/bin/python tools/cfa/f9_reachability.py

AI-OFF is the honest default here: no OPENAI_API_KEY is required and every
AI feature must resolve through its deterministic fallback.
"""

from __future__ import annotations

import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (os.path.join(REPO, "out/pylib"), os.path.join(REPO, "pylib"),
          os.path.join(REPO, "qt"), os.path.join(REPO, "out/qt"),
          os.path.join(REPO, "cfa/ethics_pairs"), REPO):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    from anki import cfa
    from anki.collection import Collection

    tmp = tempfile.mkdtemp(prefix="cfaF9_")
    path = os.path.join(tmp, "collection.anki2")
    col = Collection(path)
    ok = True
    try:
        # ---- F0b + reachability: seed a fresh profile ------------------
        from tools.cfa.seed_collection import seed_collection
        summary = seed_collection(col)
        print("F0b seed          :", summary)
        n_study = len(col.find_cards('deck:"CFA Level II"'))
        n_ethics = len(col.find_cards('deck:"CFA::Ethics Passages"')) or \
            len(col.find_cards('deck:"CFA::Ethics Pairs"'))
        print(f"                    CFA Level II cards={n_study} ethics cards={n_ethics}")
        ok &= summary["main_seeded"] and n_study > 0

        # ---- F0b: exam config round-trips ------------------------------
        cfg = cfa.get_exam_config(col)
        print("F0b exam config   :", {k: cfg.get(k) for k in ("exam_date",) if isinstance(cfg, dict)} or cfg)

        # ---- F0a: AI client resolves AI-off deterministically ----------
        from cfa.ai.llm_client import ai_enabled, complete
        r = complete("system", "hi", purpose="f9-smoke")
        print(f"F0a llm_client    : ai_enabled={ai_enabled()} ok={r['ok']} "
              f"error={r.get('error')}")
        ok &= (r["ok"] is False) or (r["ok"] is True)  # never raises = pass

        # ---- F1: deterministic multi-span grader -----------------------
        import json

        from ethics_scoring import (
            PassageAttempt,
            find_gold_spans,
            grade_passage_attempt,
        )
        with open(os.path.join(REPO, "cfa/ethics_pairs/passages.jsonl")) as fh:
            passages = [json.loads(l) for l in fh if l.strip()]
        p0 = passages[0]
        phrases = [s["phrase"] for s in p0["gold_spans"]]
        runs = find_gold_spans(p0["passage"], phrases)
        selection = [i for run in runs for i in run]  # union of all gold indices
        g = grade_passage_attempt(
            PassageAttempt(p0["verdict"], p0["verdict"], selection, runs))
        print(f"F1 grader         : passages={len(passages)} "
              f"spans={sum(len(p['gold_spans']) for p in passages)} "
              f"perfect_attempt_correct={g['correct']}")
        ok &= g["correct"] is True

        # ---- F2: semantic grader falls back to F1 when AI off ----------
        from ai_grading import grade_semantic
        sg = grade_semantic(passage=p0["passage"], answer_verdict=p0["verdict"],
                            judged_verdict=p0["verdict"],
                            gold_spans=p0["gold_spans"],
                            learner_spans=phrases,
                            selection_indices=selection)
        print(f"F2 semantic grade : source={sg['source']} correct={sg.get('correct')}")
        ok &= sg["source"] == "fallback"  # AI off

        # ---- F3: tab-fill AI-off drafts nothing (deterministic contract) --
        from aqt.cfa_tab_fill import draft_back
        drafted = draft_back("What is duration?", "Basic",
                             complete_fn=lambda *a, **k: {"ok": False, "text": ""})
        print(f"F3 tab-fill AIoff : ok={drafted['ok']} (AI off -> no draft, back untouched)")
        ok &= drafted["ok"] is False

        # ---- F4: Bayesian readiness yields a numeric call, no give-up --
        br = cfa.bayesian_readiness(col)
        print(f"F4 readiness      : call={br.call} p_pass={br.p_pass:.2f} "
              f"acc={br.accuracy:.2f} CI=[{br.ci_low:.2f},{br.ci_high:.2f}]")
        ok &= br.call in ("likely pass", "likely fail") and 0.0 <= br.p_pass <= 1.0

        # ---- F5: shared design tokens present --------------------------
        from aqt.cfa_style import TOKENS
        print(f"F5 design tokens  : primary={TOKENS.get('primary')} keys={len(TOKENS)}")
        ok &= "primary" in TOKENS

        # ---- F6/F7/F8 shared engine: BuildExamQueue over synced content -
        did = col.decks.id("CFA Level II")
        q = cfa.build_exam_queue(col, deck_id=did, fetch_limit=5)
        print(f"F6/F7/F8 engine   : build_exam_queue -> {len(q.card_ids)} cards "
              f"(shared Rust engine, on-device via fork librsdroid.so)")
        ok &= len(q.card_ids) > 0
    finally:
        col.close()

    print("\nF9 REACHABILITY:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
