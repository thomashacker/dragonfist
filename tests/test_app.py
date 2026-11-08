import json
import time

import pygame

import scenes


def frames(app, acts=(), n=3, dt=0.02):
    app.frame(list(acts), time.monotonic())
    for _ in range(n):
        time.sleep(dt)
        app.frame([], time.monotonic())


def top(app):
    return type(app.stack[-1]).__name__


def to_title(app):
    frames(app, ["ok"])
    assert top(app) == "Title"


def test_intro_runs_through(app):
    it = app.stack[-1]
    it.t0 = time.monotonic() - 20
    frames(app, n=1)
    assert top(app) == "Title"


def test_intro_skip_and_title_back_keeps_running(app):
    to_title(app)
    frames(app, ["back", "back"])
    assert top(app) == "Title" and app.running


def test_navigate_all_scenes(app):
    to_title(app)
    frames(app, ["down", "ok"])
    assert top(app) == "Arena"
    for k in range(4):
        frames(app, ["ok"])
        assert top(app) == "Placeholder"
        frames(app, ["back", "down"])
    frames(app, ["back", "down", "ok"])
    assert top(app) == "Settings"
    frames(app, ["back", "down", "ok"])
    assert top(app) == "Calibration"
    frames(app, ["ok"])
    assert app.st.mark[0] == 0
    frames(app, ["back", "up", "up", "up", "ok"])
    assert top(app) == "Placeholder"


def test_sim_punch(app):
    to_title(app)
    app.sim_punch("R")
    frames(app, n=4)
    r = app.toast
    assert r["ok"] and r["hand"] == "R" and 9 < r["v"] * 3.6 < 33


def test_sim_keys(app):
    to_title(app)
    ev = lambda t, k: pygame.event.Event(t, key=k)
    frames(app, app.input.events([ev(pygame.KEYDOWN, pygame.K_q)]))
    frames(app, app.input.events([ev(pygame.KEYDOWN, pygame.K_w)]))
    frames(app, app.input.events([ev(pygame.KEYUP, pygame.K_q), ev(pygame.KEYUP, pygame.K_w)]), n=4)
    assert app.toast["ok"] and app.toast["hand"] == "L"
    frames(app, app.input.events([ev(pygame.KEYDOWN, pygame.K_LEFT)]), n=4)
    assert app.toast["hand"] == "L" and top(app) == "Title"


def test_settings_persist(app):
    import main
    to_title(app)
    app.push(scenes.Settings(app))
    st = app.stack[-1]
    st.sel = 1
    frames(app, ["left", "left"])
    st.sel = 4
    frames(app, ["right"])
    cfg = json.loads(main.CFG_FILE.read_text(encoding="utf-8"))
    assert cfg["volume"] == 60 and cfg["abstand"] == 205
    assert app.st.punch.dist == 0.205
    st.sel = 2
    frames(app, ["ok"])
    assert not app.cfg["ton"]


def test_quit_from_settings(app):
    to_title(app)
    app.push(scenes.Settings(app))
    app.stack[-1].sel = 5
    frames(app, ["ok"])
    assert not app.running
