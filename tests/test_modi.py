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


def test_faustregen_kurve_und_ende(app):
    import regen
    assert regen.takt([0, 0.5, 1.0, 1.5], 1.6) == 2.0 and regen.takt([0, 0.5, 1.0, 1.5], 3.5) == 0.5
    assert regen.ziel(0) == 1.0 and regen.ziel(20) == 1.5 and regen.ziel(1000) == regen.MAX
    to_title(app)
    frames(app, ["ok", "left", "ok"])
    sc = app.stack[-1]
    assert top(app) == "Faustregen" and sc.phase == "warten"
    t0 = time.monotonic()
    schlag = lambda t: sc.punch(dict(ok=True, t=t, hand="L", v=2.0, vb=None, am=1, bm=64))
    schlag(t0)
    assert sc.phase == "laeuft" and sc.start == t0
    sc.t_last = t0
    for k in range(1, 41):                                  # 10 s genau im Zieltakt: Ente bleibt sicher
        t = t0 + k * 0.25
        sc.schritt(t)
        if k % round(4 / regen.ziel(t - t0)) == 0:
            schlag(t)
    assert sc.sicher() and sc.luft == 1.0
    for k in range(1, 21):                                  # aufhören: sinkt langsam, erst nach Sekunden raus
        sc.schritt(t0 + 10 + k * 0.25)
        if k == 8:
            assert sc.sicher()
    assert not sc.sicher() and sc.hoehe < 0 and sc.luft < 1.0
    sc.schritt(t0 + 30)
    assert sc.phase == "aus"
    sc.t_aus = time.monotonic() - 2
    frames(app, n=1)
    st = app.stack[-1].st
    assert top(app) == "Stats" and st["disz"] == "FAUSTREGEN" and st["n"] > 10
    frames(app, ["ok", "ok", "ok"])
    e = rangliste(app.scores, "FAUSTREGEN")
    assert top(app) == "Highscore" and len(e) == 1 and e[0]["ziel"] == st["ziel"]
