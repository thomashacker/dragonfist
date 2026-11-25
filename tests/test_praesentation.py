import random
import time

import pygame

import praesentation as P
from test_app import frames, top, to_title


def _held(app, sek):
    app.input.gelb = time.monotonic() - sek
    return app.input.events([])


def test_gelb_fuenf_sekunden_startet(app):
    to_title(app)
    assert _held(app, 1) == [] and app.input.gelb
    acts = _held(app, 5.1)
    assert acts == ["praesentation"] and app.input.gelb is None
    frames(app, acts)
    assert top(app) == "Praesentation"
    frames(app, ["praesentation"])
    assert sum(type(s).__name__ == "Praesentation" for s in app.stack) == 1


def test_ablauf_licht_konfetti_und_ende(app):
    to_title(app)
    app.push(P.Praesentation(app, random.Random(1)))
    sc = app.stack[-1]
    frames(app, n=1)
    t = time.monotonic()
    for u, erwartet in ((5, "L 000000 000000"), (P.DROPS[0] + 0.1, "L ffffff ffffff")):
        sc.t0 = t - u
        assert sc.licht(t) == erwartet
    sc.t0 = time.monotonic() - P.ENTHUELLEN - 0.05
    frames(app, n=1)
    assert sc.drop == 2 and len(sc.konfetti) > 200
    assert app.led_sent.startswith(("L", "T", "W"))
    sc.t0 = time.monotonic() - P.ENDE - 0.1
    frames(app, n=2)
    assert top(app) == "Title"


def test_abbruch_mit_knopf(app):
    to_title(app)
    app.push(P.Praesentation(app))
    frames(app, n=2)
    frames(app, ["back"])
    sc = app.stack[-1]
    assert sc.stopp is not None
    sc.t0 -= P.ABBRUCH_S + 0.1
    frames(app, n=2)
    assert top(app) == "Title"


def test_alle_rahmen_zeichnen(app):
    to_title(app)
    app.push(P.Praesentation(app, random.Random(2)))
    sc, s = app.stack[-1], pygame.Surface((1024, 600))
    t = time.monotonic()
    for u in range(0, int(P.ENDE), 3):
        sc.t0, sc.t_alt = t - u, t - u - 0.02
        sc.draw(s, t)
        sc.licht(t)
