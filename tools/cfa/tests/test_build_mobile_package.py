# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Feature F7 — tests for the CFA mobile study package builder.

``build_mobile_package.build_package`` bundles the two CFA study decks the phone
ships with (``CFA Level II`` + ``CFA::Ethics Pairs`` — the minimal-pairs flagship)
into a single importable ``.apkg`` (whole-collection export), mirroring the desktop
first-launch seeder so both platforms ship the one identical ethics deck. These
tests require a built pylib (they open a real Collection), so they are guarded by
``importorskip("anki")``.
"""

# pylint: disable=import-error,protected-access,redefined-outer-name

from __future__ import annotations

import importlib.util
import os
import zipfile

import pytest

REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
TOOLS_CFA = os.path.join(REPO, "tools", "cfa")
ETHICS_TEMPLATES = os.path.join(REPO, "cfa", "ethics_pairs", "templates")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_mobile_package = _load(
    "cfa_build_mobile_package", os.path.join(TOOLS_CFA, "build_mobile_package.py")
)


def test_builder_targets_the_minimal_pairs_flagship_not_one_passage():
    """INC4 retirement guard: the mobile builder must bundle the minimal-pairs flagship, and must not
    reference the retired one-passage importer. This is a source-level guard so a future edit that
    re-introduces the one-passage bundling fails fast, independent of a pylib build.
    """
    src = open(
        os.path.join(TOOLS_CFA, "build_mobile_package.py"), encoding="utf-8"
    ).read()
    assert "import import_pairs" in src
    assert "import passages" not in src  # the one-passage importer is retired here
    assert "CFA::Ethics Passages" not in src


@pytest.fixture()
def built_apkg(tmp_path):
    pytest.importorskip("anki")
    col = str(tmp_path / "mobile.anki2")
    apkg = str(tmp_path / "cfa-mobile.apkg")
    summary = build_mobile_package.build_package(col, apkg)
    return apkg, summary


def test_package_bundles_both_decks(built_apkg):
    apkg, summary = built_apkg
    assert os.path.exists(apkg)
    # The authored CFA Level II deck is large; ethics is exactly the 30 minimal pairs (the flagship).
    assert summary["cfa_notes"] > 200
    assert summary["ethics_notes"] == 30
    assert summary["ethics_deck"] == "CFA::Ethics Pairs"
    assert summary["ethics_notetype"] == "CFA Ethics Minimal-Pair"
    assert summary["topics"] >= 1


def test_apkg_is_a_valid_anki_package(built_apkg):
    apkg, _ = built_apkg
    # A whole-collection .apkg must contain a collection db + media manifest.
    with zipfile.ZipFile(apkg) as zf:
        names = set(zf.namelist())
    assert "media" in names, f"missing media manifest; got {sorted(names)[:8]}"
    assert any(
        n.startswith("collection.anki2") or n == "collection.anki21b" for n in names
    ), f"missing collection db; got {sorted(names)[:8]}"


def test_reimport_roundtrip_contains_both_decks(built_apkg, tmp_path):
    """Import the built package into a fresh collection and assert both decks land.

    This mirrors what the phone does on first launch (importAnkiPackage), so it is
    the desktop-side proof that the bundled package yields both study decks.
    """
    pytest.importorskip("anki")
    apkg, summary = built_apkg

    from anki.collection import Collection

    dest = str(tmp_path / "dest.anki2")
    col = Collection(dest)
    try:
        # Import through the Rust backend — the exact code path the phone uses
        # on first launch (importAnkiPackage), not the legacy Python importer.
        opts = col._backend.get_import_anki_package_presets()
        col._backend.import_anki_package(package_path=apkg, options=opts)
        deck_names = {d.name for d in col.decks.all_names_and_ids()}
        assert "CFA Level II" in deck_names
        assert "CFA::Ethics Pairs" in deck_names
        assert "CFA::Ethics Passages" not in deck_names  # one-passage no longer bundled
        # Every bundled note made it across.
        total = summary["cfa_notes"] + summary["ethics_notes"]
        assert col.card_count() >= total
    finally:
        col.close()


def test_reimport_roundtrip_contains_phone_feature_manifest(built_apkg, tmp_path):
    """The package carries machine-readable CFA feature metadata as a synced internal note.

    This gives phone/fork consumers a package-level manifest without requiring
    native Android source to live in this repository.
    """
    pytest.importorskip("anki")
    apkg, _ = built_apkg

    from anki.cfa_internal_state import get_cfa_state_record
    from anki.collection import Collection

    dest = str(tmp_path / "dest-manifest.anki2")
    col = Collection(dest)
    try:
        opts = col._backend.get_import_anki_package_presets()
        col._backend.import_anki_package(package_path=apkg, options=opts)

        manifest = get_cfa_state_record(col, build_mobile_package.PACKAGE_MANIFEST_KEY)
        assert manifest is not None
        assert manifest["package"] == "cfa-mobile-apkg"
        assert manifest["decks"] == {
            "main": "CFA Level II",
            "ethics": "CFA::Ethics Pairs",
        }
        assert manifest["notetypes"] == {
            "main": "CFA Knowledge",
            "ethics": "CFA Ethics Minimal-Pair",
        }
        assert "minimal-pair-ethics-touch-highlighting" in manifest["phoneSupported"]
        assert "server-side-ethics-semantic-feedback" in manifest["phoneSupported"]
        assert "cfa-concept-map-shell" in manifest["requiresNativeClient"]
    finally:
        col.close()


def test_bundled_ethics_is_the_multispan_flagship(built_apkg, tmp_path):
    """The bundled ethics deck is the minimal-pairs flagship with the multi-span GoldSpans key.

    Imports the package into a fresh collection and asserts an ethics note carries the JSON GoldSpans
    answer key (mirroring the one-passage contract) so the phone ships the graded multi-span flagship,
    not the retired one-passage deck.
    """
    pytest.importorskip("anki")
    import json

    apkg, _ = built_apkg
    from anki.collection import Collection

    dest = str(tmp_path / "dest2.anki2")
    col = Collection(dest)
    try:
        opts = col._backend.get_import_anki_package_presets()
        col._backend.import_anki_package(package_path=apkg, options=opts)
        nids = col.find_notes('note:"CFA Ethics Minimal-Pair"')
        assert len(nids) == 30
        note = col.get_note(nids[0])
        assert "GoldSpans" in note
        spans = json.loads(note["GoldSpans"])
        assert spans and all("phrase" in s and "rationale" in s for s in spans)
        assert any(t == "ethics::minimal-pair" for t in note.tags)
    finally:
        col.close()


def test_bundled_ethics_template_has_mobile_semantic_feedback(built_apkg, tmp_path):
    """The imported APKG carries the current Android proxy grading template.

    This is stronger than a source-only guard: it proves the exported package
    contains the same notetype template the phone imports.
    """
    pytest.importorskip("anki")
    apkg, _ = built_apkg
    from anki.collection import Collection

    dest = str(tmp_path / "dest-template.anki2")
    col = Collection(dest)
    try:
        opts = col._backend.get_import_anki_package_presets()
        col._backend.import_anki_package(package_path=apkg, options=opts)
        model = col.models.by_name("CFA Ethics Minimal-Pair")
        assert model is not None
        qfmt = model["tmpls"][0]["qfmt"]
        afmt = model["tmpls"][0]["afmt"]

        with open(os.path.join(ETHICS_TEMPLATES, "front.html"), encoding="utf-8") as f:
            current_front = f.read()
        assert qfmt == current_front

        assert "learnerHighlights: learnerHighlights()" in qfmt
        assert "selectionIndices: effSel" in qfmt
        assert "goldSpans: goldSpansPayload" in qfmt
        assert "window.CFA_AI_GRADING_ENABLED === false" in qfmt
        assert "window.CFA_AI_PROXY_URL || defaultProxyUrl()" in qfmt
        assert '"http://10.0.2.2:27702"' in qfmt
        assert '"http://127.0.0.1:27702"' in qfmt
        assert 'fetch(proxyUrl + "/cfa/grade"' in qfmt
        assert '"Authorization": "Bearer " + proxyToken' in qfmt
        assert '"proxy_unreachable"' in qfmt
        assert 'typeof resp === "string"' in qfmt
        assert "return JSON.parse(resp);" in qfmt
        # the per-highlight critique (per_learner_span) render block ships in the bundled template
        assert "resp.per_learner_span" in qfmt
        assert "cfa-ai-perhighlight" in qfmt
        assert "Your highlights, one by one" in qfmt
        assert "AI feedback" in afmt
    finally:
        col.close()
