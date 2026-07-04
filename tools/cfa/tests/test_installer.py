# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for A13 — the packaged-installer verifier.

The verifier is stdlib-only, so these build synthetic ``.app`` bundle trees in
a temp dir (no 225MB DMG required, deterministic in CI) and assert every check
fires: a good CFA bundle PASSes, a stock-Anki bundle FAILs on the missing CFA
modules, a non-self-contained bundle FAILs, and a versionless bundle FAILs.

A final opt-in test verifies the *real* clean-install bundle at
``/tmp/cfa-clean-install`` when present (the one screenshotted for evidence),
and is skipped otherwise so the suite stays green on a clean checkout.
"""

from __future__ import annotations

import importlib.util
import plistlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
VERIFY_PATH = REPO / "tools" / "cfa" / "verify_installer.py"
REAL_BUNDLE = Path("/tmp/cfa-clean-install/Applications/Anki.app")


def _load():
    import sys

    spec = importlib.util.spec_from_file_location("cfa_verify_installer", VERIFY_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cfa_verify_installer"] = mod
    spec.loader.exec_module(mod)
    return mod


V = _load()


def _make_bundle(
    root: Path,
    *,
    version: str | None = "26.5",
    python: bool = True,
    qt: bool = True,
    cfa: bool = True,
) -> Path:
    """Build a synthetic Anki.app tree with the parts we ask for."""
    app = root / "Anki.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    if version is not None:
        info = {"CFBundleShortVersionString": version, "CFBundleName": "Anki"}
        (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    if python:
        py = contents / "Frameworks" / "Python.framework"
        py.mkdir(parents=True)
        (py / "Python").write_bytes(b"\x00stub")
    pkg = contents / "Resources" / "app_packages"
    pkg.mkdir(parents=True)
    if qt:
        (pkg / "PyQt6").mkdir()
    if cfa:
        for mod in V.REQUIRED_CFA_MODULES:
            p = pkg / (mod + ".pyc")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\x00pyc")
    return app


def test_good_bundle_passes(tmp_path):
    app = _make_bundle(tmp_path)
    rep = V.verify_app(app)
    assert rep.ok
    assert rep.version == "26.5"
    assert rep.self_contained_python and rep.self_contained_qt
    assert len(rep.found_cfa) == len(V.REQUIRED_CFA_MODULES)
    assert not rep.missing_cfa
    assert V.main([str(app)]) == 0


def test_stock_anki_without_cfa_fails(tmp_path):
    app = _make_bundle(tmp_path, cfa=False)
    rep = V.verify_app(app)
    assert not rep.ok
    assert set(rep.missing_cfa) == set(V.REQUIRED_CFA_MODULES)
    assert any("missing CFA modules" in p for p in rep.problems)
    assert V.main([str(app)]) == 1


def test_partial_cfa_fails(tmp_path):
    app = _make_bundle(tmp_path)
    # remove one required module -> must be reported missing and fail
    victim = app / "Contents" / "Resources" / "app_packages" / "aqt" / "cfa_home.pyc"
    victim.unlink()
    rep = V.verify_app(app)
    assert not rep.ok
    assert "aqt/cfa_home" in rep.missing_cfa


def test_not_self_contained_python_fails(tmp_path):
    app = _make_bundle(tmp_path, python=False)
    rep = V.verify_app(app)
    assert not rep.ok
    assert not rep.self_contained_python
    assert any("Python.framework" in p for p in rep.problems)


def test_not_self_contained_qt_fails(tmp_path):
    app = _make_bundle(tmp_path, qt=False)
    rep = V.verify_app(app)
    assert not rep.ok
    assert not rep.self_contained_qt
    assert any("PyQt6" in p for p in rep.problems)


def test_missing_version_fails(tmp_path):
    app = _make_bundle(tmp_path, version=None)
    rep = V.verify_app(app)
    assert not rep.ok
    assert rep.version is None
    assert any("CFBundleShortVersionString" in p for p in rep.problems)


def test_missing_bundle_dir_fails(tmp_path):
    rep = V.verify_app(tmp_path / "Nope.app")
    assert not rep.ok
    assert any("not a bundle directory" in p for p in rep.problems)


def test_accepts_stripped_py_sources(tmp_path):
    # Briefcase strips .py, but a not-yet-compiled tree with .py should also pass.
    app = _make_bundle(tmp_path, cfa=False)
    pkg = app / "Contents" / "Resources" / "app_packages"
    for mod in V.REQUIRED_CFA_MODULES:
        p = pkg / (mod + ".py")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# stub\n")
    rep = V.verify_app(app)
    assert rep.ok
    assert len(rep.found_cfa) == len(V.REQUIRED_CFA_MODULES)


def test_format_report_mentions_result(tmp_path):
    app = _make_bundle(tmp_path)
    text = V.format_report(V.verify_app(app))
    assert "RESULT: PASS" in text
    assert "self-contained py: yes" in text


@pytest.mark.skipif(
    not REAL_BUNDLE.is_dir(),
    reason="real clean-install bundle not present (built ad hoc for A13 evidence)",
)
def test_real_clean_install_bundle():
    rep = V.verify_app(REAL_BUNDLE)
    assert rep.ok, rep.problems
    assert rep.self_contained_python and rep.self_contained_qt
    assert not rep.missing_cfa
