# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A3 tests — memory-model calibration (Brier / log loss / reliability chart).

Stdlib only; no built pylib. Covers the metric math against hand-computable
cases, the reliability-table structure, PNG rendering, the real-revlog path,
and the SIMULATED labelling contract.
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.dirname(HERE)
sys.path.insert(0, EVAL_DIR)

import calibration as C  # noqa: E402


def test_brier_hand_computed():
    # ((0.9-1)^2 + (0.2-0)^2 + (0.6-1)^2 + (0.3-0)^2) / 4
    scores = [0.9, 0.2, 0.6, 0.3]
    labels = [1, 0, 1, 0]
    expect = (0.01 + 0.04 + 0.16 + 0.09) / 4
    assert abs(C.brier_score(scores, labels) - expect) < 1e-12
    # A perfect predictor scores 0; a fully-wrong one scores 1.
    assert C.brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert C.brier_score([0.0, 1.0], [1, 0]) == 1.0


def test_log_loss_hand_computed():
    # single confident-correct prediction -> -ln(p)
    assert abs(C.log_loss([0.8], [1]) - (-math.log(0.8))) < 1e-9
    assert abs(C.log_loss([0.2], [0]) - (-math.log(0.8))) < 1e-9
    # clipping keeps a p=1, y=0 mistake finite (not inf)
    v = C.log_loss([1.0], [0])
    assert math.isfinite(v) and v > 20


def test_reliability_bins_partition():
    scores = [0.05, 0.15, 0.95, 1.0]
    labels = [0, 1, 1, 1]
    table = C.reliability_bins(scores, labels, bins=10)
    assert len(table) == 10
    # every scored item lands in exactly one bin
    assert sum(r["count"] for r in table) == len(scores)
    # the p=1.0 item is folded into the last bin, not dropped
    assert table[-1]["count"] == 2


def test_ece_matches_run_eval():
    # calibration's ECE (via its own bin table) equals run_eval's _ece.
    import run_eval

    sim = run_eval.simulate(seed=3, learners=40)
    m = C.compute(sim["scores"], sim["labels"], bins=10)
    ref = run_eval._ece(sim["scores"], sim["labels"], bins=10)
    assert abs(m["ece"] - ref) < 1e-9


def test_compute_ranges_on_sim():
    import run_eval

    sim = run_eval.simulate(seed=0, learners=100)
    m = C.compute(sim["scores"], sim["labels"])
    assert m["n"] == sim["concepts"] * 2 * 100
    assert 0.0 <= m["brier"] <= 1.0
    assert m["log_loss"] > 0.0
    assert 0.0 <= m["ece"] <= 1.0
    # The model has real signal: better than a Brier of the base-rate constant.
    base = m["base_rate"]
    const_brier = base * (1 - base)  # Brier of always predicting base rate
    assert m["brier"] < const_brier


def test_png_is_valid(tmp_path):
    import run_eval

    sim = run_eval.simulate(seed=0, learners=20)
    m = C.compute(sim["scores"], sim["labels"])
    out = str(tmp_path / "cal.png")
    C.render_reliability_png(m, out, simulated=True)
    data = open(out, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature"
    w, h = struct.unpack(">II", data[16:24])
    assert (w, h) == (460, 460)
    assert len(data) > 1000


def test_revlog_path_not_simulated(tmp_path):
    # A supplied real revlog drops the SIMULATED label and is scored as-is.
    rl = tmp_path / "revlog.jsonl"
    rows = [{"pred": 0.9, "outcome": 1}, {"pred": 0.1, "outcome": 0},
            {"pred": 0.7, "outcome": 1}, {"pred": 0.4, "outcome": 0}]
    rl.write_text("\n".join(json.dumps(r) for r in rows))
    scores, labels = C.load_revlog(str(rl))
    assert scores == [0.9, 0.1, 0.7, 0.4]
    assert labels == [1, 0, 1, 0]
    out = str(tmp_path / "rl.png")
    rc = C.main(["--revlog", str(rl), "--png", out, "--json"])
    assert rc == 0
    assert os.path.exists(out)


def test_main_simulated_exit_zero(tmp_path, capsys):
    out = str(tmp_path / "m.png")
    rc = C.main(["--seed", "1", "--learners", "20", "--png", out, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["simulated"] is True
    assert payload["chart"] == out
    assert "brier" in payload and "log_loss" in payload
