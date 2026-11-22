import json
import time

import pytest

from pico import State, NAME, GP
from runlog import RunLog


@pytest.fixture
def st(tmp_path):
    s = State(RunLog(tmp_path, NAME, GP), 200)
    yield s
    s.rl.close()


def hit(st, a=0, b=6, t0=1_000_000, dt=40_000):
    for line in (f"E {a} 1 {t0 - 1}", f"E {b} 1 {t0 - 1}", f"E {a} 0 {t0}", f"E {b} 0 {t0 + dt}",
                 f"E {a} 1 {t0 + dt + 30_000}", f"E {b} 1 {t0 + dt + 40_000}"):
        st.feed(line)


def test_parse_lines(st):
    st.feed("S 1ffe")
    assert st.ch[0].v == 0 and st.ch[1].v == 1 and st.ch[0].seen0
    st.feed("H 1 4605 251 43944 293533")
    assert st.health == dict(vbus=1, vsys=4.605, temp=25.1, scan=43944, up=293.533)
    st.feed("I 1 f8d8 6 7")
    assert st.info == dict(ver=1, uid="f8d8")


def test_breaks_and_log(st):
    hit(st)
    assert st.ch[0].breaks == 1 and st.ch[6].breaks == 1
    assert len(st.log) == 6 and st.log[0][1] == 6


@pytest.mark.parametrize("line", ["", "   ", "X", "E 1", "E a b c", "H 1 2", "S zz", "E 99 0 5", "I"])
def test_garbage_does_not_raise(st, line):
    st.feed(line)


def test_bad_lines_counted(st):
    for line in ("X", "E 1", "S zz"):
        st.feed(line)
    assert st.rl.bad == 3


def test_tick_queues_hit_and_sound(st):
    hit(st)
    time.sleep(0.04)
    st.tick(time.monotonic())
    assert len(st.hits) == 1 and st.hits[0]["ok"]
    assert "punkt" in st.sfx and "a" in st.sfx and "bruch" in st.sfx


def test_connect_resets_channels(st):
    hit(st)
    st.connect("COM6")
    assert all(c.v is None and not c.seen0 for c in st.ch)
    assert "verbunden" in st.sfx


def test_runlog_summary(st, tmp_path):
    hit(st)
    st.feed("E 0 0 2000000")
    st.feed("E 0 1 2001000")
    time.sleep(0.04)
    st.tick(time.monotonic())
    st.rl.flush(True)
    s = json.loads((st.rl.dir / "summary.json").read_text(encoding="utf-8"))
    assert s["kanaele"]["A1"]["brueche"] == 2 and s["kanaele"]["A1"]["glitches"] == 1
    assert s["kanaele"]["B1"]["brueche"] == 1
    assert s["schlaege"]["ok"] == 1
    assert (st.rl.dir / "punches.csv").read_text(encoding="utf-8").count("TREFFER") == 1


def test_stuck_channel_marked_dead(st):
    st.feed("S %x" % (((1 << 13) - 1) & ~(1 << 8)))
    t = time.monotonic()
    st.tick(t)
    assert not st.ch[8].dead(t) and st.punch.low
    st.tick(t + 6)
    assert st.ch[8].dead(t + 6) and st.punch.dead == 1 << 8 and not st.punch.low
    st.feed("E 8 1 5")
    st.tick(time.monotonic())
    assert not st.ch[8].dead(time.monotonic()) and st.punch.dead == 0


def test_hit_without_speed_is_logged_and_shown(st):
    r = dict(t=0.0, ok=True, v=None, vb=None, dt=None, a=0, b=6, hand="L", msg="TREFFER", n=1, am=1, bm=64)
    st.rl.punch(r)
    st.rl.flush(True)
    s = json.loads((st.rl.dir / "summary.json").read_text(encoding="utf-8"))
    assert s["schlaege"]["ok"] == 1 and s["schlaege"]["mittel_km_h"] is None


def test_schreiben_replaces_whole_file(tmp_path):
    from runlog import schreiben
    f = tmp_path / "highscores.json"
    schreiben(f, {"a": 1})
    schreiben(f, {"b": 2})
    assert json.loads(f.read_text(encoding="utf-8")) == {"b": 2} and not list(tmp_path.glob("*.tmp"))
