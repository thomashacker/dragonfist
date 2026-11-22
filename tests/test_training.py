import time

import pytest

from training import auswerten, rangliste, Stats, SEITE_S
from test_app import frames, top, to_title


def r(t, hand, v, vb=None, am=1, bm=1 << 6, ok=True):
    return dict(t=t, hand=hand, ok=ok, v=v, vb=vb, am=am, bm=bm)


def test_auswerten():
    p = [r(0.5, "L", 5.0, 2.5), r(1.0, "R", 10.0, am=1 << 5, bm=1 << 12), r(3.0, "L", 5.0), r(3.5, "L", None, ok=False)]
    st = auswerten(p, 4.0)
    assert (st["n"], st["nl"], st["nr"], st["fehl"]) == (3, 2, 1, 1)
    assert st["v_avg"] == pytest.approx(24.0) and st["vb_avg"] == pytest.approx(9.0) and st["v_max"] == pytest.approx(36)
    assert st["takt"] == [1.0, 0.5] and st["takt_avg"] == pytest.approx(0.75)
    assert st["wege"][0] == ("L", pytest.approx(1 / 12), pytest.approx(1 / 14))
    assert 0 < st["genau"] < 30 and st["streu"]["L"] == pytest.approx(0)


def test_training_flow_saves_highscore(app):
    to_title(app)
    frames(app, ["ok", "ok"])
    assert top(app) == "Training"
    for hand in "LRLLR":
        app.sim_punch(hand)
        frames(app, n=3)
    assert len(app.stack[-1].punches) == 5
    frames(app, ["back"])
    st = app.stack[-1]
    assert isinstance(st, Stats) and st.st["n"] == 5 and st.st["nl"] == 3 and len(st.st["zur"]) == 5
    for i in range(5):
        st.t0 = time.monotonic() - i * SEITE_S - 3
        frames(app, n=1)
        assert st.seite == i
    frames(app, ["ok", "ok"])
    assert top(app) == "NameEntry"
    frames(app, ["up", "right", "up", "ok"])
    assert top(app) == "Highscore" and len(app.stack) == 2
    e = rangliste(app.scores, "TRAINING")
    assert len(e) == 1 and e[0]["name"] == "BA" and e[0]["n"] == 5
    frames(app, ["back"])
    assert top(app) == "Title"


def test_training_without_punches_returns(app):
    to_title(app)
    frames(app, ["ok", "ok"])
    frames(app, ["back"])
    assert top(app) == "Modes"


def test_discard_goes_home(app):
    to_title(app)
    frames(app, ["ok", "ok"])
    app.sim_punch("L")
    frames(app, n=3)
    frames(app, ["back", "ok", "right", "ok"])
    assert top(app) == "Title" and not app.scores.exists()


def test_aufnahme_logs_truth(app, tmp_path):
    from aufnahme import Aufnahme
    notes = []
    app.st.note = notes.append
    app.push(Aufnahme(app))
    sc = app.stack[-1]
    frames(app, ["right", "right", "down", "left", "ok"])
    assert sc.dauer == 15 and sc.phase == "countdown"
    sc.t0 = time.monotonic() - 4
    frames(app, n=1)
    assert sc.phase == "laeuft" and notes == ["AUFNAHME START dauer=15 person=1 art=SCHNELL"]
    app.sim_punch("L")
    app.sim_punch("R")
    frames(app, n=4)
    sc.t0 = time.monotonic() - 16
    frames(app, n=1)
    assert sc.phase == "zaehlen" and sc.zahl == 2
    frames(app, ["up", "right", "ok"])
    assert sc.phase == "fertig" and notes[-1] == "AUFNAHME ENDE erkannt=2 L=1 R=1 fehl=0 gezaehlt=13"
    frames(app, ["ok"])
    assert sc.phase == "wahl" and sc.wert(1) == "SCHNELL" and sc.dauer == 15


def test_hit_without_speed_in_training_and_overlay(app):
    to_title(app)
    frames(app, ["ok", "ok"])
    tr = app.stack[-1]
    frames(app, n=1)
    r = dict(t=time.monotonic(), ok=True, v=None, vb=None, dt=None, a=0, b=6, hand="L", msg="TREFFER", n=1, am=1, bm=64)
    with app.st.lock:
        app.st.hits.append(r)
    frames(app, n=2)
    app.sim_punch("R")
    frames(app, n=4)
    frames(app, ["back"])
    st = app.stack[-1].st
    assert st["n"] == 2 and len(st["hin"]) == 1
    for i in range(5):
        app.stack[-1].t0 = time.monotonic() - i * SEITE_S - 3
        frames(app, n=1)
