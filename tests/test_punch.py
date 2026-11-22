from pathlib import Path

import pytest

from punch import Punch, WRAP


def one(p, now):
    r = p.tick(now)
    return r[0] if r else None

A1, A6, B1, B7 = 0, 5, 6, 12


def run(edges, dist=200, settle=0.05):
    p = Punch(6, 13, dist)
    t = 0.0
    for ch, v, tus in edges:
        t += 0.001
        p.edge(ch, v, tus, t)
    assert one(p, t + 0.01) is None
    return p, one(p, t + settle)


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
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.0)
    p.edge(A1, 1, 150_000, 0.15)
    r = one(p, 0.2)
    assert not r["ok"] and r["msg"] == "NICHT DURCH"
    assert p.events == [("a", "L"), ("fehl", "L")]


def test_short_wipe_through_a_is_ignored():
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.0)
    p.edge(A1, 1, 30_000, 0.03)
    assert p.tick(0.2) == [] and p.events == [("a", "L")]


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
    assert one(p, 0.005) is None
    p.edge(A1, 0, 2_000, 0.006)
    p.edge(B1, 0, 40_000, 0.040)
    p.edge(A1, 1, 70_000, 0.070)
    p.edge(B1, 1, 80_000, 0.080)
    r = one(p, 0.2)
    assert r["ok"] and r["dt"] == 40_000


def test_waits_until_all_clear():
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.0)
    p.edge(B1, 0, 40_000, 0.04)
    p.edge(A1, 1, 60_000, 0.06)
    assert one(p, 1.0) is None
    p.edge(B1, 1, 70_000, 1.0)
    assert one(p, 1.01) is None
    assert one(p, 1.1)["ok"]


def test_status_mask_releases():
    p = Punch(6, 13, 200)
    p.edge(A1, 0, 0, 0.0)
    p.edge(B1, 0, 40_000, 0.04)
    p.status((1 << 13) - 1, 0.1)
    assert one(p, 0.2)["ok"]


def test_counter_and_best():
    p = Punch(6, 13, 200)
    t = 0.0
    for dt in (40_000, 20_000, 80_000):
        for ch, v, tus in punch(A1, B1, int(t * 1e6), dt):
            t += 0.01
            p.edge(ch, v, tus, t)
        t += 0.1
        one(p, t)
    assert p.n == 3 and p.best == pytest.approx(10.0)


def test_dead_channel_ignored():
    p = Punch(6, 13, 200)
    p.status(((1 << 13) - 1) & ~(1 << 8), 0.0)
    assert p.low
    p.set_dead(1 << 8, 6.0)
    assert not p.low
    p.status(((1 << 13) - 1) & ~(1 << 8), 6.1)
    p.edge(A1, 0, 0, 6.2)
    p.edge(B1, 0, 40_000, 6.24)
    p.edge(A1, 1, 60_000, 6.26)
    p.edge(B1, 1, 70_000, 6.27)
    assert one(p, 6.4)["ok"]


def test_both_hands_at_once():
    p = Punch(6, 13, 200)
    for ch, v, tus, t in ((A1, 0, 0, 0.0), (A6, 0, 5_000, 0.005), (B7, 0, 25_000, 0.025), (B1, 0, 40_000, 0.04),
                          (A6, 1, 60_000, 0.06), (B7, 1, 70_000, 0.07), (A1, 1, 80_000, 0.08)):
        p.edge(ch, v, tus, t)
    r = p.tick(0.075 + 0.03)
    assert [x["hand"] for x in r] == ["R"] and r[0]["dt"] == 20_000
    assert one(p, 0.2) is None
    p.edge(B1, 1, 90_000, 0.09)
    r = one(p, 0.2)
    assert r["hand"] == "L" and r["dt"] == 40_000 and p.n == 2
    assert p.events == [("a", "L"), ("a", "R"), ("b", "R"), ("b", "L"), ("punkt", "R"), ("punkt", "L")]


def test_left_fist_crossing_to_right_b_is_one_left_hit():
    p = Punch(6, 13, 200)
    for ch, v, tus, t in ((1, 0, 0, 0.0), (2, 0, 5_000, 0.005), (10, 0, 40_000, 0.04), (10, 1, 90_000, 0.09),
                          (2, 1, 120_000, 0.12), (1, 1, 130_000, 0.13)):
        p.edge(ch, v, tus, t)
    r = p.tick(0.3)
    assert [(x["hand"], x["ok"]) for x in r] == [("L", True)] and r[0]["b"] == 10


def test_arm_staying_in_a_counts_each_push_through_b():
    p = Punch(6, 13, 200)
    p.edge(1, 0, 0, 0.0)
    t = 0.0
    for k in range(3):
        tb = 60_000 + k * 250_000
        p.edge(1 + (k > 0), 0, tb - 50_000, tb / 1e6 - 0.05) if k else None
        p.edge(7, 0, tb, tb / 1e6)
        p.edge(7, 1, tb + 80_000, tb / 1e6 + 0.08)
        t = tb / 1e6 + 0.1
        p.tick(t)
    p.edge(2, 1, 900_000, 0.9)
    p.edge(1, 1, 900_000, 0.9)
    p.tick(1.0)
    assert p.n == 3


def test_two_fists_side_by_side_stay_apart():
    p = Punch(6, 13, 200)
    for ch, v, tus, t in ((2, 0, 0, 0.0), (3, 0, 2_000, 0.002), (4, 0, 4_000, 0.004), (8, 0, 40_000, 0.04),
                          (10, 0, 45_000, 0.045), (8, 1, 90_000, 0.09), (10, 1, 95_000, 0.095), (2, 1, 120_000, 0.12),
                          (3, 1, 121_000, 0.121), (4, 1, 122_000, 0.122)):
        p.edge(ch, v, tus, t)
    r = p.tick(0.3)
    assert sorted(x["hand"] for x in r if x["ok"]) == ["L", "R"]


def test_replay_fast_alternating_training():
    import analyse
    ev, st, _ = analyse.laden(Path(__file__).parent / "data" / "schnell")
    res = analyse.abspielen(ev, st, Punch)
    ok = [r for r in res if r["ok"]]
    nl = sum(r["hand"] == "L" for r in ok)
    assert 100 <= len(ok) <= 110 and abs(2 * nl - len(ok)) <= 6 and len(res) - len(ok) <= 5


def test_retraction_speed_and_path_masks():
    p = Punch(6, 13, 200)
    for ch, v, tus, t in ((A1, 0, 0, 0.0), (1, 0, 2_000, 0.002), (B1, 0, 40_000, 0.04), (B1, 1, 100_000, 0.1),
                          (1, 1, 150_000, 0.15), (A1, 1, 180_000, 0.18)):
        p.edge(ch, v, tus, t)
    r = one(p, 0.3)
    assert r["vb"] == pytest.approx(0.2 / 0.08) and r["am"] == 0b11 and r["bm"] == 1 << B1


def test_replay_training_with_crossing_arms():
    import analyse
    ev, st, _ = analyse.laden(Path(__file__).parent / "data" / "training2")
    res = analyse.abspielen(ev, st, Punch)
    ok = [r for r in res if r["ok"]]
    assert 89 <= len(ok) <= 95 and len(res) - len(ok) <= 5
