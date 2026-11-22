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
    frames(app, ["ok"])
    assert top(app) == "Modes"
    frames(app, ["ok"])
    assert top(app) == "Training"
    frames(app, ["back", "back", "right", "ok"])
    assert top(app) == "Settings"
    app.stack[-1].sel = 5
    frames(app, ["ok"])
    assert top(app) == "Calibration"
    frames(app, ["ok"])
    assert app.st.mark[0] == 0
    frames(app, ["back", "back", "left", "ok"])
    assert top(app) == "Modes"


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
    app.stack[-1].sel = len(app.stack[-1].rows) - 1
    frames(app, ["ok"])
    assert not app.running


def test_version_shown(app):
    to_title(app)
    assert app.version.count(".") == 2


def test_bundled_font(app):
    from monitor import FONT
    assert FONT.exists()
    assert app.font.f["xl"].size("DRAGONFIST")[0] < scenes.W


def test_cursor_hidden(app):
    assert not pygame.mouse.get_visible()


def test_music_follows_scene(app):
    app.force_mute = False
    frames(app, n=1)
    assert app.track is None
    to_title(app)
    assert app.track == "title"
    frames(app, ["ok", "ok"])
    assert top(app) == "Training" and app.track == "action"
    frames(app, ["back", "back", "right", "ok"])
    assert top(app) == "Settings" and app.track == "title"
    app.stack[-1].sel = 5
    frames(app, ["ok"])
    assert top(app) == "Calibration" and app.track is None
    frames(app, ["back"])
    app.cfg["ton"] = False
    frames(app, n=1)
    assert app.track is None


def test_leds_dance_in_menu_and_follow_punch_in_mode(app):
    to_title(app)
    assert app.st.out[-1] == "T"
    frames(app, ["ok", "ok"])
    assert top(app) == "Training" and app.st.out[-1] == "L 000000 000000"
    app.sim_punch("R")
    frames(app, n=4)
    assert app.st.out[-1] == "L 000000 0050ff"
    assert [r["hand"] for r in app.stack[-1].punches if r["ok"]] == ["R"]
    for hand in "LR":
        app.led[hand] = ("punkt", time.monotonic() - 1)
    frames(app, n=1)
    assert app.st.out[-1] == "L 000000 000000"
