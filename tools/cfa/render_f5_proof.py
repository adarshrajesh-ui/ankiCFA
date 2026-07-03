# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render REAL offscreen/headless proof of the F5 UI overhaul.

Grabs the ACTUAL desktop surfaces (no mocks) to PNG so the shared CFA design
system can be compared before/after and across surfaces:

* ``f5-readiness-<tag>.png`` — the real ``aqt.cfa.ExamReadinessDialog`` against a
  seeded collection (hero call + three bands + per-topic table).
* ``f5-deadline-<tag>.png``  — the real ``aqt.cfa.DeadlineDialog`` with due cards
  ranked weakest-first.
* ``f5-ethics-card-<tag>.png`` — the real one-passage ethics card (F1 template +
  shared style.css) rendered with headless Chrome.

Run it once BEFORE the styling change (``--tag before``) and once AFTER
(``--tag after``) for an honest side-by-side.

Usage:
    QT_QPA_PLATFORM=offscreen out/pyenv/bin/python tools/cfa/render_f5_proof.py --tag before
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from anki import cfa as anki_cfa
from anki.collection import Collection
from aqt import cfa

DAY = 86_400
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(REPO, "proof", "gnhf2")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class _MW(QWidget):
    def __init__(self, col: Collection) -> None:
        super().__init__()
        self.col = col

    def reset(self) -> None:
        pass

    def moveToState(self, state: str) -> None:
        pass


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def _seed(col: Collection, topic: str, n_cards: int, reviews_each: int, frac_ok: float):
    """Seed a deck with FSRS memory state + a first-exposure correctness mix."""
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id("CFA")
    cids = []
    for i in range(n_cards):
        note = col.new_note(nt)
        note["Front"] = f"{topic}-{i}"
        note["Back"] = "a"
        note.tags = [f"{topic}::r1"]
        col.add_note(note, deck)
        cids.append(col.find_cards(f"nid:{note.id}")[0])
    col.sched.set_due_date(cids, "0")
    data = json.dumps({"s": 100.0, "d": 5.0, "lrt": now - DAY})
    col.db.executemany(
        "update cards set data=?, ivl=? where id=?", [(data, 20, c) for c in cids]
    )
    n_ok = round(n_cards * frac_ok)
    first_ease = [3] * n_ok + [1] * (n_cards - n_ok)
    base = (col.db.scalar("select coalesce(max(id),0) from revlog") or 0) + 1
    rows, k = [], 0
    for idx, c in enumerate(cids):
        for j in range(reviews_each):
            ease = first_ease[idx] if j == 0 else 3
            rows.append((base + k, c, -1, ease, 10, 5, 2500, 1000, 1))
            k += 1
    col.db.executemany(
        "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type)"
        " values (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    anki_cfa.set_exam_config(col, exam_date="2026-12-01", topic_weights={topic: 1.0})
    return deck


def _save(widget: QWidget, name: str, w: int, h: int) -> str:
    widget.resize(w, h)
    path = os.path.join(OUT_DIR, name)
    if not widget.grab().save(path):
        raise RuntimeError(f"failed to save {path}")
    print(f"wrote {path}")
    return path


def _render_dialogs(tag: str) -> None:
    col = _empty_col()
    try:
        deck = _seed(col, "los::ethics", n_cards=40, reviews_each=8, frac_ok=0.82)
        col.decks.select(deck)  # so the deadline view ranks this deck's due cards
        mw = _MW(col)

        dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]
        _save(dlg, f"f5-readiness-{tag}.png", 680, 620)
        dlg.close()

        dl = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
        _save(dl, f"f5-deadline-{tag}.png", 620, 560)
        dl.close()
    finally:
        col.close()


def _render_ethics_card(tag: str) -> None:
    """Generate the real F1 card HTML then screenshot it with headless Chrome."""
    html_path = os.path.join(OUT_DIR, f"f5-ethics-card-{tag}.html")
    png_path = os.path.join(OUT_DIR, f"f5-ethics-card-{tag}.png")
    gen = subprocess.run(
        [
            os.path.join(REPO, "out", "pyenv", "bin", "python"),
            os.path.join(HERE, "render_f1_passage.py"),
            "--item",
            "PSG-17",
            "--out",
            html_path,
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    print(gen.stdout.strip().split("\n")[-1][:80])
    subprocess.run(
        [
            CHROME,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            "--window-size=980,900",
            f"--screenshot={png_path}",
            f"file://{html_path}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"wrote {png_path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="after", choices=["before", "after"])
    ap.add_argument("--skip-card", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    app = QApplication.instance() or QApplication(["render"])
    assert app is not None
    cfa.tooltip = lambda *a, **k: None  # type: ignore[assignment]

    _render_dialogs(args.tag)
    if not args.skip_card and os.path.exists(CHROME):
        _render_ethics_card(args.tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
