#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA fork — A13: packaged-installer verifier.

Given a path to a packaged macOS ``Anki.app`` bundle (as unpacked from the
Briefcase ``.dmg`` produced by ``just installer`` / ``tools/build-installer``),
this asserts three things that make it a *shippable, clean-machine-installable*
CFA build rather than stock Anki or a dev tree:

  1. **self-contained** — the bundle carries its own ``Python.framework`` and
     ``PyQt6`` so it runs on a machine with no Python/Qt installed;
  2. **is the CFA fork** — the required CFA modules are compiled into the
     bundle (``anki/cfa*``, ``aqt/cfa*``), with sources stripped to ``.pyc``;
  3. **versioned** — ``Info.plist`` carries a ``CFBundleShortVersionString``.

It is stdlib-only (no anki import, no Qt) so it runs anywhere, and it is the
programmatic half of the A13 evidence: the ordered clean-machine install
screenshot sequence lives in ``proof/friday/gnhf-speedrun/L1/installer/``.

Usage::

    tools/cfa/verify_installer.py /path/to/Anki.app
    tools/cfa/verify_installer.py --dmg out/installer/dist/anki-*.dmg  # macOS

Exit code 0 = valid CFA installer bundle, 1 = a required check failed.
"""

from __future__ import annotations

import argparse
import plistlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

# CFA modules that MUST be baked into a real fork build. Kept in sync with the
# fork's cfa_* source files; if a new one is added it should appear here so the
# installer check fails loudly rather than silently shipping a stale bundle.
REQUIRED_CFA_MODULES = (
    "anki/cfa",
    "anki/cfa_sync",
    "anki/cfa_deadline",
    "aqt/cfa",
    "aqt/cfa_home",
    "aqt/cfa_chrome",
    "aqt/cfa_sync_connect",
    "aqt/cfa_seed",
)


@dataclass
class Report:
    """Outcome of verifying one bundle."""

    app: Path
    version: str | None = None
    self_contained_python: bool = False
    self_contained_qt: bool = False
    found_cfa: list[str] = field(default_factory=list)
    missing_cfa: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _resources_dir(app: Path) -> Path:
    return app / "Contents" / "Resources"


def _module_present(pkg_root: Path, dotted: str) -> bool:
    """True if ``dotted`` (e.g. ``aqt/cfa_home``) is compiled into the bundle.

    Briefcase strips ``.py`` sources and ships legacy ``.pyc`` next to where the
    source used to be, so we accept either form.
    """
    rel = Path(dotted)
    return (pkg_root / rel.with_suffix(".pyc")).is_file() or (
        pkg_root / rel.with_suffix(".py")
    ).is_file()


def verify_app(app: Path) -> Report:
    rep = Report(app=app)
    if not app.is_dir():
        rep.problems.append(f"not a bundle directory: {app}")
        return rep

    contents = app / "Contents"
    info = contents / "Info.plist"
    if info.is_file():
        try:
            plist = plistlib.loads(info.read_bytes())
            rep.version = plist.get("CFBundleShortVersionString")
        except Exception as exc:  # pragma: no cover - corrupt plist
            rep.problems.append(f"could not read Info.plist: {exc}")
    else:
        rep.problems.append("missing Contents/Info.plist")
    if not rep.version:
        rep.problems.append("Info.plist has no CFBundleShortVersionString")

    # self-contained runtime
    py_fw = contents / "Frameworks" / "Python.framework" / "Python"
    rep.self_contained_python = py_fw.is_file()
    if not rep.self_contained_python:
        rep.problems.append("no bundled Python.framework (not self-contained)")

    pkg_root = _resources_dir(app) / "app_packages"
    rep.self_contained_qt = (pkg_root / "PyQt6").is_dir()
    if not rep.self_contained_qt:
        rep.problems.append("no bundled PyQt6 (not self-contained)")

    # is the CFA fork
    if not pkg_root.is_dir():
        rep.problems.append(f"no app_packages dir under Resources: {pkg_root}")
    else:
        for mod in REQUIRED_CFA_MODULES:
            if _module_present(pkg_root, mod):
                rep.found_cfa.append(mod)
            else:
                rep.missing_cfa.append(mod)
        if rep.missing_cfa:
            rep.problems.append(
                "missing CFA modules (stock Anki, not the fork?): "
                + ", ".join(rep.missing_cfa)
            )

    return rep


def format_report(rep: Report) -> str:
    lines = [
        "CFA packaged-installer verification",
        "===================================",
        f"bundle:            {rep.app}",
        f"version:           {rep.version or '(none)'}",
        f"self-contained py: {'yes' if rep.self_contained_python else 'NO'}",
        f"self-contained qt: {'yes' if rep.self_contained_qt else 'NO'}",
        f"CFA modules found: {len(rep.found_cfa)}/{len(REQUIRED_CFA_MODULES)}",
    ]
    for mod in REQUIRED_CFA_MODULES:
        mark = "ok " if mod in rep.found_cfa else "MISS"
        lines.append(f"  [{mark}] {mod}")
    lines.append("")
    lines.append("RESULT: PASS" if rep.ok else "RESULT: FAIL")
    for prob in rep.problems:
        lines.append(f"  - {prob}")
    return "\n".join(lines)


def mount_dmg(dmg: Path) -> tuple[Path, Path]:
    """Attach a .dmg read-only and return (mountpoint, app_path). macOS only."""
    mnt = Path(tempfile.mkdtemp(prefix="cfa-dmg-"))
    subprocess.check_call(
        [
            "hdiutil",
            "attach",
            str(dmg),
            "-readonly",
            "-nobrowse",
            "-mountpoint",
            str(mnt),
        ]
    )
    apps = list(mnt.glob("*.app"))
    if not apps:
        subprocess.call(["hdiutil", "detach", str(mnt)])
        raise RuntimeError(f"no .app found in {dmg}")
    return mnt, apps[0]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_installer", description="Verify a packaged CFA installer."
    )
    parser.add_argument("app", nargs="?", help="Path to Anki.app bundle")
    parser.add_argument("--dmg", help="Path to a .dmg to mount and verify (macOS)")
    args = parser.parse_args(argv)

    if not args.app and not args.dmg:
        parser.error("provide an Anki.app path or --dmg")

    mnt: Path | None = None
    try:
        if args.dmg:
            if sys.platform != "darwin":
                print("--dmg mounting is macOS-only", file=sys.stderr)
                return 1
            mnt, app = mount_dmg(Path(args.dmg))
        else:
            app = Path(args.app)
        rep = verify_app(app)
        print(format_report(rep))
        return 0 if rep.ok else 1
    finally:
        if mnt is not None:
            subprocess.call(["hdiutil", "detach", str(mnt)])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
