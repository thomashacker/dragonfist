import os
import sys
import time
from argparse import Namespace

import pytest

import splash


def test_status_fresh_and_stale(tmp_path, monkeypatch):
    f = tmp_path / "status"
    monkeypatch.setattr(splash, "STATUS", f)
    assert splash.status() is None
    f.write_text("UPDATE AUF v9.9.9 …\n", encoding="utf-8")
    assert splash.status() == "UPDATE AUF v9.9.9 …"
    old = time.time() - 3600
    os.utime(f, (old, old))
    assert splash.status() is None


@pytest.mark.skipif(sys.platform == "win32", reason="flock")
def test_lock_marks_app_running(tmp_path, monkeypatch):
    monkeypatch.setattr(splash, "STATE", tmp_path)
    monkeypatch.setattr(splash, "LOCK", tmp_path / "app.lock")
    assert not splash.app_running()
    held = splash.hold_lock()
    assert held and splash.app_running()
    held.close()
    assert not splash.app_running()


def test_reader_stops_on_exit(tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "CFG_FILE", tmp_path / "settings.json")
    a = main.App(Namespace(sim=False, port="nichtda", abstand=None, fullscreen=False, mute=True, no_log=True,
                           runs=str(tmp_path)))
    a.run(str(tmp_path / "s.png"))
    import pygame
    pygame.quit()
    assert not a.reader.is_alive()


def test_reader_wakes_silent_pico(monkeypatch):
    import threading
    import monitor

    geschrieben = []

    class Stumm:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def readline(self):
            time.sleep(0.01)
            return b""

        def write(self, b):
            geschrieben.append(b)

    monkeypatch.setattr(monitor.serial, "Serial", Stumm)
    st, stop = monitor.State(None, 200), threading.Event()
    th = threading.Thread(target=monitor.reader, args=(st, "x", stop, 0.05))
    th.start()
    time.sleep(0.4)
    stop.set()
    th.join(2)
    assert geschrieben and geschrieben[0] == monitor.WECKEN


def test_reader_joins_split_lines(monkeypatch):
    import threading
    import monitor

    teile = [b"E 3 0 50", b"6293698\n", b"S 1fff\n"]

    class Zerhackt:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def readline(self):
            time.sleep(0.005)
            return teile.pop(0) if teile else b""

        def write(self, b):
            pass

    monkeypatch.setattr(monitor.serial, "Serial", Zerhackt)
    st, stop = monitor.State(None, 200), threading.Event()
    gelesen = []
    monkeypatch.setattr(st, "feed", gelesen.append)
    th = threading.Thread(target=monitor.reader, args=(st, "x", stop))
    th.start()
    time.sleep(0.1)
    stop.set()
    th.join(2)
    assert gelesen == ["E 3 0 506293698\n", "S 1fff\n"]
