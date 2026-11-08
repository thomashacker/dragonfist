import time

import scenes
from monitor import State
from punch import Punch


def best_of(fn, n=3):
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t)
    return min(out)


def test_feed_throughput():
    st = State(None, 200)
    lines = [f"E {i % 13} {i // 13 % 2} {i * 50}" for i in range(10_000)]

    def go():
        for line in lines:
            st.feed(line)
    assert best_of(go) < 0.25


def test_punch_logic_throughput():
    p = Punch(6, 13, 200)

    def go():
        t = 0.0
        for k in range(20_000):
            for ch, v, o in ((0, 0, 0), (6, 0, 40_000), (0, 1, 70_000), (6, 1, 80_000)):
                p.edge(ch, v, k * 200_000 + o, t)
                t += 0.01
            p.tick(t + 0.1)
    assert best_of(go) < 0.5


def frame_time(app, n=30):
    t = time.perf_counter()
    for _ in range(n):
        app.frame([], time.monotonic())
    return (time.perf_counter() - t) / n


def test_frame_budget(app):
    app.frame(["ok"], time.monotonic())
    assert frame_time(app) < 0.008
    app.push(scenes.Calibration(app))
    for _ in range(5):
        app.sim_punch("L")
    assert frame_time(app) < 0.012
