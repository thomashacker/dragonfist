import random
import time

import modi
from training import rangliste
from test_app import frames, top, to_title


def test_zeit_countdown_limit_and_highscore(app):
    to_title(app)
    frames(app, ["ok", "right", "ok"])
    assert top(app) == "Setup"
    frames(app, ["left", "down", "down"])
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
    frames(app, ["ok", "ok", "ok", "down", "down", "right", "ok"])
    e = rangliste(app.scores, "ZEIT")
    assert top(app) == "Highscore" and len(e) == 1 and e[0]["ziel"] == 10 and e[0]["n"] == 3


def test_setup_edits_each_digit(app):
    app.cfg |= dict(zeit_limit=30, reak_runden=10, reak_kombo=1)
    app.push(modi.zeit(app))
    frames(app, ["left", "down", "down", "down", "left", "up", "up"])
    assert app.cfg["zeit_limit"] == 120
    frames(app, ["down", "down", "right", "up", "right", "up", "up"])
    assert app.cfg["zeit_limit"] == 12
    frames(app, ["down", "down", "left", "down"])
    assert app.cfg["zeit_limit"] == 0 and app.stack[-1].wert(0) == 0
    frames(app, ["ok"])
    assert top(app) == "Zeit" and app.stack[-1].limit == 1
    app.pop()
    app.push(modi.reaktion(app))
    frames(app, ["right", "up", "up", "left", "left", "down"])
    assert (app.cfg["reak_runden"], app.cfg["reak_kombo"]) == (0, 3)


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
    sc = app.stack[-1]
    frames(app, ["right"])
    assert sc.seite == 1 and not sc.auto
    frames(app, ["left", "left"])
    assert sc.seite == 4
    sc.t0 -= 30
    frames(app, n=1)
    assert sc.seite == 4


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
    frames(app, ["ok", "ok", "ok", "down", "down", "right", "ok"])
    assert top(app) == "Highscore" and rangliste(app.scores, "REAKTION")[0]["kombo"] == 2


def test_faustregen_nur_zu_langsam_zaehlt(app):
    import regen
    assert regen.takt([9.0, 9.5, 10.0], 10.4, 0) == 1.0 and regen.takt([10.0], 10.4, 10.0) == 1.0
    assert regen.ziel(0) == 1.0 and regen.ziel(200) == 6.0
    app.push(regen.Faustregen(app))
    frames(app, n=1)
    sc = app.stack[-1]
    assert sc.phase == "warten"
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
    frames(app, ["ok", "ok", "ok", "down", "down", "right", "ok"])
    e = rangliste(app.scores, "FAUSTREGEN")
    assert top(app) == "Highscore" and len(e) == 1 and e[0]["ziel"] == st["ziel"]


def test_punkte_durchhalten(app):
    from modi import Punkte
    sp = Punkte(app)
    app.push(sp)
    t = 100.0
    treffer = lambda hand, v=None: dict(ok=True, hand=hand, v=v, t=t, tb_s=t, am=1, bm=1 << 6)
    sp.punch(dict(ok=False, hand="L", v=None, t=t, tb_s=t, am=1, bm=0))
    assert sp.start is None
    sp.punch(treffer("L", 5.0))
    assert sp.start == t and sp.punkte == 10 + 18
    for k in range(1, 61):
        t = 100.0 + k * 0.2
        sp.tick(t)
        sp.t_draw = t
        sp.punch(treffer("R" if k % 2 else "L"))
    assert sp.mult(t) == 2 and sp.mult_max == 2 and sp.energie > 0
    sp.tick(t + 1.2)
    assert sp.mult(t + 1.2) == 1
    sp.t_draw = t + 1.2
    sp.tick(t + 10)
    assert sp.t_ende is not None and sp.energie == 0
    frames(app, n=1)
    sp.t_ende -= 2
    frames(app, n=1)
    assert top(app) == "Stats" and app.stack[-1].st["punkte"] == sp.punkte
