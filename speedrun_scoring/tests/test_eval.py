from speedrun_scoring import eval as eval_mod


def test_eval_runs_and_exits_zero(capsys):
    rc = eval_mod.run()
    out = capsys.readouterr().out
    assert rc == 0
    assert "calibration" in out
    assert "paraphrase gap" in out
    assert "RESULT: OK" in out
