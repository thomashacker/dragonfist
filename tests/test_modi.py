import random
import time

import modi
from training import rangliste
from test_app import frames, top, to_title


def test_zeit_countdown_limit_and_highscore(app):
    to_title(app)
    frames(app, ["ok", "right", "ok"])
    assert top(app) == "Setup"
    frames(app, ["left", "left"])
    assert app.cfg["zeit_limit"] == 10
    frames(app, ["ok"])
    sc = app.stack[-1]
    assert top(app) == "Zeit" and sc.phase == "countdown"
    app.sim_punch("L")
    frames(app, n=4)
    sc.t0 = time.monotonic() - 6
    frames(app, n=1)
    assert sc.phase == "laeuft" and not sc.punches
    for hand in "LRL":
        app.sim_punch(hand)
        frames(app, n=4)
    sc.start = time.monotonic() - 11
    frames(app, n=1)
    sc.ende = time.monotonic() - 1
    frames(app, n=1)
    assert top(app) == "Stats" and app.stack[-1].st["n"] == 3 and app.stack[-1].st["ziel"] == 10
    frames(app, ["ok", "ok", "ok"])
    e = rangliste(app.scores, "ZEIT")
    assert top(app) == "Highscore" and len(e) == 1 and e[0]["ziel"] == 10 and e[0]["n"] == 3


def test_serie_stops_at_target(app):
    app.cfg["serie_n"] = 10
    app.push(modi.serie(app))
    frames(app, ["ok"])
    sc = app.stack[-1]
    assert top(app) == "Serie" and sc.ziel == 10 and sc.start is None
    for k in range(10):
        app.sim_punch("LR"[k % 2])
        frames(app, n=3)
    assert sc.dauer is not None and sc.dauer > 0
    sc.t_ende = time.monotonic() - 2
    frames(app, n=1)
    st = app.stack[-1].st
    assert top(app) == "Stats" and st["n"] == 10 and st["disz"] == "SCHLÄGE"


def test_reaktion_combo_and_false_start(app):
    app.push(modi.Reaktion(app, 2, 2, random.Random(1)))
    sc = app.stack[-1]
    frames(app, n=1)
    assert sc.phase == "warten"
    app.sim_punch("L")
    frames(app, n=4)
    assert sc.fehlstart == 1 and sc.phase == "anzeige"
    for _ in range(2):
        sc.t_phase = time.monotonic() - 2
        frames(app, n=1)
        sc.t_piep = time.monotonic() - 0.01
        frames(app, n=1)
        assert sc.phase == "jetzt"
        app.sim_punch("L")
        frames(app, n=4)
        assert sc.phase == "jetzt"
        app.sim_punch("R")
        frames(app, n=4)
        assert sc.phase == "anzeige"
    sc.t_phase = time.monotonic() - 2
    frames(app, n=2)
    st = app.stack[-1].st
    assert top(app) == "ReaktionStats" and len(st["zeiten"]) == 2 and 0 < st["r_best"] <= st["r_avg"] < 0.5
    frames(app, ["ok", "ok", "ok"])
    assert top(app) == "Highscore" and rangliste(app.scores, "REAKTION")[0]["kombo"] == 2


def test_faustregen_nur_zu_langsam_zaehlt(app):
    import regen
    assert regen.takt([9.0, 9.5, 10.0], 10.4, 0) == 1.0 and regen.takt([10.0], 10.4, 10.0) == 1.0
    assert regen.ziel(0) == 1.0 and regen.ziel(200) == 6.0
    to_title(app)
    frames(app, ["ok", "left", "ok"])
    sc = app.stack[-1]
    assert top(app) == "Faustregen" and sc.phase == "warten"
    assert "W 1000 00ff00" in app.st.out
    t0 = time.monotonic()
    schlag = lambda t: sc.punch(dict(ok=True, t=t, hand="L", v=2.0, vb=None, am=1, bm=64))
    schlag(t0)
    assert sc.phase == "laeuft" and sc.start == t0
    sc.t_last = t0
    for k in range(1, 81):                                  # 20 s doppelt so schnell wie verlangt: oben, sicher
        t = t0 + k * 0.25
        sc.schritt(t)
        schlag(t)
    assert sc.hoehe == 1.0 and sc.luft == 1.0 and sc.rate >= 3.9
    for k in range(1, 41):                                  # aufhören: sinkt, Takt fällt sanft statt auf 0
        sc.schritt(t0 + 20 + k * 0.25)
        if k == 4:
            assert sc.sicher() and sc.rate > 2
    assert not sc.sicher() and sc.luft < 1.0
    sc.schritt(t0 + 40)
    assert sc.phase == "aus"
    sc.t_aus = time.monotonic() - 2
    frames(app, n=1)
    st = app.stack[-1].st
    assert top(app) == "Stats" and st["disz"] == "FAUSTREGEN" and st["n"] == 81
    frames(app, ["ok", "ok", "ok"])
    e = rangliste(app.scores, "FAUSTREGEN")
    assert top(app) == "Highscore" and len(e) == 1 and e[0]["ziel"] == st["ziel"]
