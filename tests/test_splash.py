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
    assert not a.reader.is_alive()
