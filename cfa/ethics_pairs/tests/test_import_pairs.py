# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Round-trip test for the jsonl -> Anki notes importer.

Requires a built pylib. Run via:
    just cfa-test
    # or directly:
    PYTHONPATH=out/pylib ANKI_TEST_MODE=1 out/pyenv/bin/python -m pytest cfa/ethics_pairs/tests/test_import_pairs.py
"""

import html
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from anki.collection import Collection
except Exception:  # pragma: no cover - only when pylib isn't built
    Collection = None

import ethics_notetype as nt  # noqa: E402
import import_pairs  # noqa: E402

pytestmark = pytest.mark.skipif(
    Collection is None, reason="requires a built pylib (PYTHONPATH=out/pylib)"
)


def _fresh_collection(tmpdir):
    return Collection(os.path.join(tmpdir, "test.anki2"))


def test_jsonl_to_notes_roundtrip():
    pairs = import_pairs.load_pairs()  # default bundled pairs.jsonl
    assert len(pairs) == 30

    with tempfile.TemporaryDirectory() as d:
        col = _fresh_collection(d)
        try:
            stats = import_pairs.import_pairs(col, pairs)
            assert stats["created"] == 30
            assert stats["updated"] == 0

            # note type has exactly the contract fields (incl. the multi-span GoldSpans), in order
            model = col.models.by_name(nt.NOTETYPE_NAME)
            assert model is not None
            assert [f["name"] for f in model["flds"]] == nt.FIELDS
            assert "GoldSpans" in nt.FIELDS

            # deck exists (sibling of main deck) and every card lives in it
            did = col.decks.id_for_name(nt.DECK_NAME)
            assert did is not None

            nids = col.find_notes(f'note:"{nt.NOTETYPE_NAME}"')
            assert len(nids) == 30

            by_pid = {}
            for nid in nids:
                note = col.get_note(nid)
                by_pid[note["PairId"]] = note
            assert len(by_pid) == 30  # PairIds unique

            src = {p["pair_id"]: p for p in pairs}
            for pid, note in by_pid.items():
                p = src[pid]
                assert note["AnswerA"] == p["answer_a"]
                assert note["AnswerB"] == p["answer_b"]
                assert note["VignetteA"] == html.escape(p["vignette_a"], quote=False)
                assert note["VignetteB"] == html.escape(p["vignette_b"], quote=False)
                assert note["DecisiveFact"] == html.escape(
                    p["decisive_fact"], quote=False
                )
                assert note["DecisivePhrase"] == html.escape(
                    p["decisive_phrase"], quote=False
                )
                assert note["DecisivePhraseCase"] == p["decisive_phrase_case"]
                # the imported decisive phrase is a verbatim substring of its vignette
                _vign = (
                    p["vignette_a"]
                    if p["decisive_phrase_case"] == "A"
                    else p["vignette_b"]
                )
                assert p["decisive_phrase"] in _vign
                assert note["DistractorFact1"] == html.escape(
                    p["distractors"][0], quote=False
                )
                assert note["DistractorFact3"] == html.escape(
                    p["distractors"][2], quote=False
                )
                assert note["Standard"] == html.escape(p["standard"], quote=False)
                assert note["ClusterTag"] == f"cluster::{p['cluster']}"

                # GoldSpans carries the multi-span answer key as JSON (mirrors one-passage). It parses
                # back to the authored spans and every phrase is verbatim in the violating vignette.
                import json as _json

                spans = _json.loads(note["GoldSpans"])
                assert spans and all("phrase" in s and "rationale" in s for s in spans)
                assert [s["phrase"] for s in spans] == [
                    g["phrase"] for g in import_pairs.gold_spans_for(p)
                ]
                for s in spans:
                    assert s["phrase"] in _vign

                # tags: the los:: ethics tag and the cluster:: tag are present
                assert p["los_tags"][0] in note.tags
                assert f"cluster::{p['cluster']}" in note.tags
                assert "ethics::minimal-pair" in note.tags

                # exactly one card, and it lives in the Ethics Pairs deck
                cards = note.cards()
                assert len(cards) == 1
                assert cards[0].did == did

            # re-import is idempotent: updates in place, creates nothing new
            stats2 = import_pairs.import_pairs(col, pairs)
            assert stats2["created"] == 0
            assert stats2["updated"] == 30
            assert len(col.find_notes(f'note:"{nt.NOTETYPE_NAME}"')) == 30
        finally:
            col.close()


def test_load_pairs_rejects_equal_answers():
    import json

    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "bad.jsonl")
        rec = {
            "pair_id": "X-01",
            "cluster": "c",
            "los_tags": ["los::ethics::x"],
            "vignette_a": "a",
            "answer_a": "violate",
            "vignette_b": "b",
            "answer_b": "violate",
            "decisive_fact": "d",
            "decisive_phrase": "a",
            "decisive_phrase_case": "A",
            "distractors": ["1", "2", "3"],
            "rationale": "r",
            "standard": "I(C)",
        }
        with open(bad, "w") as f:
            f.write(json.dumps(rec) + "\n")
        with pytest.raises(ValueError):
            import_pairs.load_pairs(bad)
