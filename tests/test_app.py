import json
import time
from pathlib import Path

import pygame

import scenes


def frames(app, acts=(), n=3, dt=0.02):
    app.frame(list(acts), time.monotonic())
    for _ in range(n):
        time.sleep(dt)
        app.frame([], time.monotonic())


def zeile(st, name):
    st.sel = [r[0] for r in st.rows].index(name)


def top(app):
    return type(app.stack[-1]).__name__


def to_title(app):
    frames(app, ["ok"])
    assert top(app) == "Title"


def test_intro_runs_through(app):
    it = app.stack[-1]
    it.t0 = time.monotonic() - 20
    frames(app, n=1)
    assert top(app) == "Title" and not pygame.mouse.get_visible()


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
    zeile(app.stack[-1], "KALIBRIERUNG")
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
    zeile(st, "LAUTSTÄRKE")
    frames(app, ["left", "left"])
    zeile(st, "ABSTAND A–B")
    frames(app, ["right"])
    cfg = json.loads(main.CFG_FILE.read_text(encoding="utf-8"))
    assert cfg["volume"] == 60 and cfg["abstand"] == 205
    assert app.st.punch.dist == 0.205
    zeile(st, "TON")
    frames(app, ["ok"])
    assert not app.cfg["ton"]
    zeile(st, "MUSIK")
    frames(app, ["right"])
    assert not json.loads(main.CFG_FILE.read_text(encoding="utf-8"))["musik"]


def _netz_ruhig(app, monkeypatch):
    """Hintergrund-Prüfung anhalten, damit sie gesetzte Werte nicht überschreibt."""
    import netz
    monkeypatch.setattr(netz.Netz, "_pruefen", lambda self: None)
    for _ in range(60):
        if app.netz.online is not None:
            break
        time.sleep(0.05)
    time.sleep(0.3)
    return app.netz


def test_wlan_wechsel(app, monkeypatch):
    n, wahl = _netz_ruhig(app, monkeypatch), []
    monkeypatch.setattr(n, "verbinden", wahl.append)
    n.ssid, n.profile, n.meldung = "Zuhause", ["Zuhause", "Handy"], None
    app.push(scenes.Settings(app))
    st = app.stack[-1]
    zeile(st, "WLAN")
    assert st.wlan_text() == "Zuhause"
    frames(app, ["ok"])
    assert not wahl
    frames(app, ["right"])
    assert st.wlan_text() == "Handy  OK?"
    frames(app, ["ok"])
    assert wahl == ["Handy"]
    aus = []
    monkeypatch.setattr(n, "trennen", lambda: aus.append(1))
    frames(app, ["right"])
    assert st.wlan_text() == "KEIN WLAN  OK?"
    frames(app, ["ok"])
    assert aus == [1]
    n.ssid, st.netz_wahl = None, None
    assert st.wlan_text() == "KEIN WLAN"
    frames(app, ["right"])
    assert st.wlan_text() == "Zuhause  OK?"


def test_update_zeile(app, monkeypatch):
    n, los = _netz_ruhig(app, monkeypatch), []
    monkeypatch.setattr(n, "installieren", lambda: los.append(1) or True)
    app.push(scenes.Settings(app))
    st = app.stack[-1]
    assert app.cfg["auto_update"] is False
    zeile(st, "AUTO-UPDATE")
    frames(app, ["right"])
    assert app.cfg["auto_update"] is True
    zeile(st, "UPDATE")
    n.update = None
    frames(app, ["ok"])
    assert not los and st.update_text().startswith("aktuell")
    n.update = "9.9.9"
    assert st.update_text().startswith("v9.9.9")
    frames(app, ["ok"])
    assert los == [1] and st.update_text() == "wird installiert …"


def test_quit_from_settings(app):
    to_title(app)
    app.push(scenes.Settings(app))
    app.stack[-1].sel = len(app.stack[-1].rows) - 1
    frames(app, ["ok"])
    assert not app.running


def test_bundled_font(app):
    from monitor import FONT
    assert FONT.exists()
    assert app.font.f["xl"].size("DRAGONFIST")[0] < scenes.QUER[0]


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
    zeile(app.stack[-1], "KALIBRIERUNG")
    frames(app, ["ok"])
    assert top(app) == "Calibration" and app.track is None
    frames(app, ["back", "back", "left", "ok"])
    assert app.track == "title"
    app.cfg["musik"] = False
    frames(app, n=1)
    assert app.track is None and not app.mute
    app.cfg["musik"], app.cfg["ton"] = True, False
    frames(app, n=1)
    assert app.track is None


def led(app):
    return next(c for c in reversed(app.st.out) if not c.startswith("D "))


def test_leds_dance_in_menu_and_follow_punch_in_mode(app):
    to_title(app)
    assert led(app) == "T"
    frames(app, ["ok", "ok"])
    assert top(app) == "Training" and led(app) == "L 000000:0 000000:0"
    app.sim_punch("R")
    frames(app, n=4)
    assert led(app) == "L 000000:0 00ff3c:19"
    assert [r["hand"] for r in app.stack[-1].punches if r["ok"]] == ["R"]
    for hand in "LR":
        app.led[hand] = ("punkt", time.monotonic() - 1)
    frames(app, n=1)
    assert led(app).endswith(":18")
    frames(app, n=40)
    assert led(app) == "L 000000:0 00ff3c:0"


def test_led_stufen_wachsen_weich(app):
    t = 100.0
    app.led_jetzt = t
    app.led["L"] = ("a", t + 1.5)
    werte = []
    for k in range(1, 8):
        werte.append(app._streifen("L", t + k * 0.016))
        app.led_jetzt = t + k * 0.016
    n = [int(w.split(":")[1]) for w in werte]
    assert n == sorted(n) and n[0] < 5 and n[-1] == 5 and werte[-1].startswith("ff5a00")
    app.led["L"] = ("fehl", t + 2)
    w = app._streifen("L", t + 0.2)
    assert w.startswith("ff0000")


def test_hochformat_umschalten_und_drehen(app):
    assert app.cfg["ausrichtung"] == "hoch_l" and app.screen.get_size() == scenes.HOCH
    to_title(app)
    app.push(scenes.Settings(app))
    zeile(app.stack[-1], "AUSRICHTUNG")
    frames(app, ["left"])
    assert app.cfg["ausrichtung"] == "quer" and app.screen.get_size() == scenes.QUER
    frames(app, ["right"])
    for sc in (scenes.Modes(app), scenes.Settings(app), scenes.Calibration(app)):
        app.push(sc)
        frames(app, n=1)
    app.voll, app.display = True, None
    app.ausrichtung()
    frames(app, n=1)
    assert app.drehen == 90 and app.screen.get_size() == scenes.HOCH and app.display.get_size() == scenes.QUER


def maus(app, *punkte, dt=0.0):
    ev = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=punkte[0])]
    app.input.events(ev)
    time.sleep(dt)
    return app.input.events([pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=punkte[-1])])


def test_touch_tippen_wischen_halten(app):
    to_title(app)
    t = app.stack[-1]
    frames(app, n=1)
    r = t.ziele[-1][1]
    assert maus(app, r.center) == [("tap", r.center)]
    assert maus(app, (100, 100), (300, 110)) == ["right"]
    assert maus(app, (100, 300), (110, 100)) == ["up"]
    app.input.events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 50))])
    time.sleep(0.85)
    assert app.input.events([]) == ["back"]
    assert app.input.events([pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(50, 50))]) == []
    frames(app, [("tap", t.ziele[0][1].center)])
    assert top(app) == "Modes"


def test_touch_leerer_fleck_und_einstellungen(app):
    to_title(app)
    frames(app, [("tap", (1, 1))])
    assert top(app) == "Title"
    st = scenes.Settings(app)
    app.push(st)
    frames(app, n=1)
    zeile(st, "ABSTAND A–B")
    k, box = next(z for z in st.ziele if z[0] == st.sel)
    v = app.cfg["abstand"]
    frames(app, [("tap", (box.right - 5, box.centery))])
    assert app.cfg["abstand"] == v + 5
    frames(app, [("tap", (box.x + 5, box.centery))])
    assert app.cfg["abstand"] == v
    andere = next(z for z in st.ziele if z[0] != st.sel)
    frames(app, [("tap", andere[1].center)])
    assert st.sel == andere[0] and app.cfg["abstand"] == v


def test_touch_drehung():
    from inputs import drehung
    w, h = 600, 1024
    bild = pygame.Surface((w, h))
    bild.set_at((10, 20), (255, 0, 0))
    for d in (90, -90, 0):
        g = pygame.transform.rotate(bild, d)
        rot = next((x, y) for x in range(g.get_width()) for y in range(g.get_height())
                   if g.get_at((x, y))[:3] == (255, 0, 0))
        assert drehung(d, w, h)(rot) == (10, 20)


def test_licht_dimmen(app):
    st = scenes.Settings(app)
    app.push(st)
    zeile(st, "LICHT")
    frames(app, ["left", "left", "left"], n=1)
    assert app.cfg["licht"] == 70
    app.led_t = 0
    frames(app, n=1)
    assert "D 70" in app.st.out


def test_geraete_check(app, monkeypatch):
    import geraete
    app.sim = False
    monkeypatch.setattr(app.st, "live", lambda now: True)
    monkeypatch.setattr(geraete, "ERWARTET", (("LAUTSPRECHER", lambda a: False), ("TOUCH", lambda a: None),
                                              ("JOYSTICK", lambda a: True)))
    app.geraete = geraete.Geraete()
    assert app.geraete.text(app, 100.0) == "FEHLT: LAUTSPRECHER"
    monkeypatch.setattr(geraete, "ERWARTET", ())
    for c in app.st.ch:
        c.v, c.t = 1, 0.0
    app.st.ch[9].v = 0
    assert app.geraete.text(app, 101.0) == "FEHLT: LAUTSPRECHER" and app.geraete.text(app, 110.0) == "FEHLT: B4"
    st = scenes.Settings(app)
    app.push(st)
    zeile(st, "GERÄTE")
    frames(app, ["ok"], n=1)
    assert top(app) == "Settings"


def test_action_song_zufaellig(app, monkeypatch, tmp_path):
    import main
    for n in ("action_theme.mp3", "action_theme_2.mp3", "title_theme.mp3"):
        (tmp_path / n).write_bytes(b"")
    geladen = []
    monkeypatch.setattr(main, "MUSIC", tmp_path)
    monkeypatch.setattr(pygame.mixer.music, "load", lambda p: geladen.append(Path(p).name))
    monkeypatch.setattr(pygame.mixer.music, "play", lambda *a, **k: None)
    app.force_mute = False
    for _ in range(30):
        app.track = None
        app.stack[-1].music = "action"
        app.music()
    assert set(geladen) == {"action_theme.mp3", "action_theme_2.mp3"}
