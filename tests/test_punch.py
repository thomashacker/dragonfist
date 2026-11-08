import pytest

from punch import Punch, WRAP

A1, A6, B1, B7 = 0, 5, 6, 12


def run(edges, dist=200, settle=0.05):
    p = Punch(6, 13, dist)
    t = 0.0
    for ch, v, tus in edges:
        t += 0.001
        p.edge(ch, v, tus, t)
    assert p.tick(t + 0.01) is None
    return p, p.tick(t + settle)


def punch(a, b, t0, dt, hold=30_000):
    return [(a, 0, t0), (b, 0, t0 + dt), (a, 1, t0 + dt + hold), (b, 1, t0 + dt + hold + 10_000)]


def test_hit_speed_and_hand():
    p, r = run(punch(A1, B1, 1_000_000, 40_000))
    assert r["ok"] and r["msg"] == "TREFFER"
    assert r["v"] == pytest.approx(5.0)
    assert r["dt"] == 40_000 and r["hand"] == "L" and r["n"] == 1
    assert p.best == pytest.approx(5.0)


def test_right_hand():
    _, r = run(punch(A6, B7, 0, 20_000))
    assert r["ok"] and r["hand"] == "R"


def test_distance_scales_speed():
    _, r = run(punch(A1, B1, 0, 40_000), dist=150)
    assert r["v"] == pytest.approx(3.75)


def test_not_through():
    _, r = run([(A1, 0, 0), (A1, 1, 50_000)])
    assert not r["ok"] and r["msg"] == "NICHT DURCH"


def test_backwards():
    _, r = run(punch(B1, A1, 0, 40_000))
    assert not r["ok"] and r["msg"] == "RÜCKWÄRTS"


@pytest.mark.parametrize("dt,msg", [(5_000, "ZU SCHNELL?"), (2_500_000, "ZU LANGSAM")])
def test_implausible(dt, msg):
    p, r = run(punch(A1, B1, 0, dt))
    assert not r["ok"] and r["msg"] == msg and p.n == 0


def test_timer_wrap():
    _, r = run(punch(A1, B1, WRAP - 10_000, 40_000))
    assert r["ok"] and r["dt"] == 40_000


def test_edge_flicker_keeps_first_break():
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.000)
    p.edge(A1, 1, 1_000, 0.001)
    assert p.tick(0.005) is None
    p.edge(A1, 0, 2_000, 0.006)
    p.edge(B1, 0, 40_000, 0.040)
    p.edge(A1, 1, 70_000, 0.070)
    p.edge(B1, 1, 80_000, 0.080)
    r = p.tick(0.2)
    assert r["ok"] and r["dt"] == 40_000


def test_waits_until_all_clear():
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.0)
    p.edge(B1, 0, 40_000, 0.04)
    p.edge(A1, 1, 60_000, 0.06)
    assert p.tick(1.0) is None
    p.edge(B1, 1, 70_000, 1.0)
    assert p.tick(1.01) is None
    assert p.tick(1.1)["ok"]


def test_status_mask_releases():
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.0)
    p.edge(B1, 0, 40_000, 0.04)
    p.status((1 << 13) - 1, 0.1)
    assert p.tick(0.2)["ok"]


def test_counter_and_best():
    p = Punch(6, 13, 200)
    t = 0.0
    for dt in (40_000, 20_000, 80_000):
        for ch, v, tus in punch(A1, B1, int(t * 1e6), dt):
            t += 0.01
            p.edge(ch, v, tus, t)
        t += 0.1
        p.tick(t)
    assert p.n == 3 and p.best == pytest.approx(10.0)
