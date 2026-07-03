#!/usr/bin/env python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Reproduction / proof harness for desktop increment ``item3`` (two sub-bugs).

Run (offscreen Qt + a real Collection), redirecting to the before/after proof:

    QT_QPA_PLATFORM=offscreen \\
      PYTHONPATH="out/pylib:pylib:qt:out/qt" \\
      out/pyenv/bin/python proof/fixes/p1/item3_repro.py

Sub-bug 3A — the Exam Readiness hero prints a confident "likely fail p=0.xx"
call from the Beta(1,1) prior even when Memory / Performance / Readiness all
correctly ABSTAIN (below the give-up threshold).

Sub-bug 3B — topic accounting is deck-fragmented: with no exam config the
``_derive_topics`` fallback derives topics from whatever cards are in scope, so
``topics_total`` varies with the selected deck (1, 2, ...) instead of the fixed
canonical CFA syllabus (8 authored topics). count/table/list are therefore not
pinned to the canonical list.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QTableWidget, QWidget

from anki import cfa as anki_cfa
from anki.collection import Collection
from aqt import cfa

DAY = 86_400
_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication(["repro"])  # type: ignore[assignment]
    return _APP  # type: ignore[return-value]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


class _StandInMW(QWidget):
    def __init__(self, col: Collection) -> None:
        _app()
        super().__init__()
        self.col = col


def _seed(col, deck_name, topic, n_cards, reviews_each, frac_ok):
    """Seed review cards under ``topic`` in ``deck_name`` (no exam config)."""
    now = int(time.time())
    nt = col.models.by_name("Basic")
    deck = col.decks.id(deck_name)
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
    return deck


def _hero_html(dlg) -> str:
    """The first (header) QLabel — it carries the F4 hero + bands + caption."""
    return dlg.findChildren(QLabel)[0].text()


def _all_text(dlg) -> str:
    return " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))


def _verdict(ok: bool) -> str:
    return "OK (fixed)" if ok else "BUG"


def repro_3a() -> None:
    print("=" * 72)
    print("SUB-BUG 3A — hero must ABSTAIN below the give-up threshold")
    print("=" * 72)
    col = _empty_col()
    # Realistic fresh-profile state: exam weights configured (as the first-launch
    # seeder does), but almost no graded reviews -> below MIN_GRADED_REVIEWS.
    deck = _seed(col, "CFA", "los::topica", n_cards=2, reviews_each=1, frac_ok=1.0)
    anki_cfa.set_exam_config(
        col, exam_date="2026-12-01", topic_weights={"los::topica": 1.0}
    )

    score = anki_cfa.memory_score(col, deck_id=deck)
    perf = anki_cfa.performance_score(col, deck_id=deck)
    ready = anki_cfa.readiness_score(col, deck_id=deck)
    bayes = anki_cfa.bayesian_readiness(col, deck_id=deck)

    print(f"graded_reviews = {score.graded_reviews} (give-up needs >= 200)")
    print(f"memory.abstain      = {score.abstain}   reason={score.reason!r}")
    print(f"performance.abstain = {perf.abstain}")
    print(f"readiness.abstain   = {ready.abstain}")
    print(f"bayes.call          = {bayes.call!r}  call_prob={bayes.call_prob:.2f}")

    mw = _StandInMW(col)
    dlg = cfa.ExamReadinessDialog(mw, deck)  # type: ignore[arg-type]
    hero = _hero_html(dlg)
    text = _all_text(dlg)
    has_p = "p=" in hero
    has_likely = "likely" in hero
    has_ci = "95% CI" in hero
    keeps = "keep studying" in hero.lower()
    bands_honest = "Not enough data" in text
    print("-" * 72)
    print(f"HERO contains 'p='            : {has_p}")
    print(f"HERO contains 'likely'        : {has_likely}")
    print(f"HERO contains '95% CI'        : {has_ci}")
    print(f"HERO says 'keep studying'     : {keeps}")
    print(f"Memory/Perf/Readiness bands abstain honestly : {bands_honest}")
    # The bug is a confident hero (p=/likely/CI) while the scores abstain. The
    # fix is an abstaining hero (keep studying, none of p=/likely/CI).
    fixed = score.abstain and not has_p and not has_likely and not has_ci and keeps
    print(
        f"VERDICT 3A: {_verdict(fixed)}  "
        f"(hero {'ABSTAINS' if fixed else 'is CONFIDENT'} below the threshold)"
    )
    dlg.close()
    col.close()


def repro_3b() -> None:
    print()
    print("=" * 72)
    print("SUB-BUG 3B — topic accounting must be canonical + consistent")
    print("=" * 72)
    print(
        f"canonical CFA topics in code = {len(anki_cfa.CANONICAL_TOPICS)}"
        if hasattr(anki_cfa, "CANONICAL_TOPICS")
        else "canonical CFA topics in code = (CANONICAL_TOPICS not defined yet)"
    )

    # No exam config -> the _derive_topics fallback derives from cards in scope.
    col = _empty_col()
    _seed(col, "CFA::EthicsOnly", "los::ethics", n_cards=5, reviews_each=3, frac_ok=0.8)
    _seed(col, "CFA::QuantOnly", "los::quant", n_cards=5, reviews_each=3, frac_ok=0.8)
    assert anki_cfa.get_exam_config(col) is None, "no exam config in this repro"

    parent = col.decks.id("CFA")
    ethics = col.decks.id("CFA::EthicsOnly")

    whole = anki_cfa.memory_score(col, deck_id=parent)
    scoped = anki_cfa.memory_score(col, deck_id=ethics)

    print("-" * 72)
    print("(i) memory_score topic total must be canonical + deck-independent:")
    print(f"    memory_score(CFA parent).topics_total      = {whole.topics_total}")
    print(f"    memory_score(CFA::EthicsOnly).topics_total = {scoped.topics_total}")
    print(f"    whole.topics list  = {[t.topic for t in whole.topics]}")
    print(f"    scoped.topics list = {[t.topic for t in scoped.topics]}")
    print(
        f"    whole.coverage_pct = {whole.coverage_pct:.3f} (denominator "
        f"{whole.topics_total}); scoped.coverage_pct = {scoped.coverage_pct:.3f} "
        f"(denominator {scoped.topics_total})"
    )
    total_ok = whole.topics_total == scoped.topics_total == 8
    list_ok = len(whole.topics) == whole.topics_total == 8
    print(
        f"    VERDICT 3B(i): {_verdict(total_ok and list_ok)}  "
        f"(total deck-independent & == canonical 8: {total_ok and list_ok})"
    )

    print("-" * 72)
    print("(ii) bayesian_readiness fallback must NOT crash with no exam config:")
    bayes_ok = False
    try:
        br = anki_cfa.bayesian_readiness(col, deck_id=parent)
        bayes_ok = br.topics_total == 8
        print(
            f"    bayesian_readiness returned normally; topics_total={br.topics_total}"
        )
    except Exception as exc:  # noqa: BLE001 - capturing the repro
        print(f"    {type(exc).__name__}: {exc}")
    print(f"    VERDICT 3B(ii): {_verdict(bayes_ok)}")

    print("-" * 72)
    print("(iii) ExamReadinessDialog must render; caption == table == list == 8:")
    dlg_ok = False
    mw = _StandInMW(col)
    try:
        dlg = cfa.ExamReadinessDialog(mw, parent)  # type: ignore[arg-type]
        table = dlg.findChild(QTableWidget)
        text = _all_text(dlg)
        caption_frag = f"/{whole.topics_total} topics"
        rows = table.rowCount()
        cap_ok = caption_frag in text
        print(f"    dialog per-topic table row count = {rows}")
        print(f"    dialog caption contains '{caption_frag}' : {cap_ok}")
        print(f"    len(score.topics) = {len(whole.topics)}")
        dlg_ok = rows == len(whole.topics) == whole.topics_total == 8 and cap_ok
        dlg.close()
    except Exception as exc:  # noqa: BLE001 - capturing the repro
        print(f"    {type(exc).__name__}: {exc}")
    print(f"    VERDICT 3B(iii): {_verdict(dlg_ok)}")
    col.close()


if __name__ == "__main__":
    repro_3a()
    repro_3b()
