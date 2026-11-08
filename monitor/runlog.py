import csv
import json
import time
from pathlib import Path

WRAP = 1 << 30
GLITCH_US = 3000
GAP_S = 0.25


class RunLog:
    def __init__(self, root, names, gps, tag=""):
        self.names, self.gps = names, gps
        self.dir = Path(root) / (time.strftime("%Y%m%d-%H%M%S") + (f"-{tag}" if tag else ""))
        self.dir.mkdir(parents=True)
        self.t0, self.start = time.monotonic(), time.strftime("%Y-%m-%dT%H:%M:%S")
        self.raw = open(self.dir / "raw.log", "w", buffering=1, encoding="utf-8")
        self._ev = open(self.dir / "events.csv", "w", buffering=1, newline="", encoding="utf-8")
        self._he = open(self.dir / "health.csv", "w", buffering=1, newline="", encoding="utf-8")
        self.ev, self.he = csv.writer(self._ev), csv.writer(self._he)
        self.ev.writerow(["t", "kanal", "v", "t_us", "dauer_us", "glitch"])
        self.he.writerow(["t", "vbus", "vsys", "temp", "scan_hz", "uptime_s"])
        self._pu = open(self.dir / "punches.csv", "w", buffering=1, newline="", encoding="utf-8")
        self.pu = csv.writer(self._pu)
        self.pu.writerow(["t", "nr", "ok", "status", "dt_us", "m_s", "km_h", "a", "b"])
        self.punches, self.v_max, self.v_sum = [0, 0], 0.0, 0.0
        self.ch = [dict(brueche=0, glitches=0, min_us=None, max_us=0, sum_us=0, n=0, t0=None, erkannt=False)
                   for _ in names]
        self.marks, self.info, self.port = [], None, None
        self.lines = self.bad = self.connects = self.gaps = self.vbus_lost = 0
        self.gap_max, self.last_s = 0.0, None
        self.rng = dict(vsys=[None, None], temp=[None, None], scan=[None, None])
        self.next_sum = self.t0 + 5

    def t(self):
        return time.monotonic() - self.t0

    def line(self, s, ok=True):
        self.lines += 1
        self.bad += not ok
        self.raw.write(f"{self.t():.4f} {'' if ok else '! '}{s}\n")

    def note(self, s):
        self.raw.write(f"{self.t():.4f} # {s}\n")

    def connect(self, port):
        self.connects += 1
        self.port, self.last_s = port, None
        self.note(f"connect {port}")

    def status(self, now, mask):
        if self.last_s is not None and now - self.last_s > GAP_S:
            self.gaps += 1
            self.gap_max = max(self.gap_max, now - self.last_s)
        self.last_s = now
        for i, c in enumerate(self.ch):
            c["erkannt"] |= not (mask >> i & 1)

    def event(self, i, v, tus):
        c, dur = self.ch[i], None
        if v == 0:
            c["brueche"] += 1
            c["erkannt"] = True
            c["t0"] = tus
        elif c["t0"] is not None:
            dur = (tus - c["t0"]) % WRAP
            c["t0"] = None
            c["n"] += 1
            c["sum_us"] += dur
            c["max_us"] = max(c["max_us"], dur)
            c["min_us"] = dur if c["min_us"] is None else min(c["min_us"], dur)
            c["glitches"] += dur < GLITCH_US
        self.ev.writerow([f"{self.t():.4f}", self.names[i], v, tus, "" if dur is None else dur,
                          int(dur is not None and dur < GLITCH_US)])
        return dur

    def health(self, h):
        self.he.writerow([f"{self.t():.4f}", h["vbus"], h["vsys"], h["temp"], h["scan"], h["up"]])
        self.vbus_lost += not h["vbus"]
        for k, r in self.rng.items():
            r[0] = h[k] if r[0] is None else min(r[0], h[k])
            r[1] = h[k] if r[1] is None else max(r[1], h[k])

    def punch(self, r):
        ok = r["ok"]
        self.punches[ok] += 1
        if ok:
            self.v_max = max(self.v_max, r["v"])
            self.v_sum += r["v"]
        self.pu.writerow([f"{self.t():.4f}", r.get("n", ""), int(ok), r["msg"], "" if r["dt"] is None else r["dt"],
                          f"{r['v']:.3f}" if ok else "", f"{r['v'] * 3.6:.1f}" if ok else "",
                          "" if r["a"] is None else self.names[r["a"]], "" if r["b"] is None else self.names[r["b"]]])
        self.note(f"PUNCH {r['msg']}" + (f" {r['v']:.2f} m/s" if ok else ""))

    def mark(self):
        n = len(self.marks) + 1
        self.marks.append(dict(n=n, t=round(self.t(), 3)))
        self.note(f"MARKER {n}")
        return n

    def summary(self):
        kan = {}
        for name, gp, c in zip(self.names, self.gps, self.ch):
            kan[name] = dict(gp=gp, erkannt=c["erkannt"], brueche=c["brueche"], glitches=c["glitches"],
                             offen=c["t0"] is not None,
                             bruch_ms=dict(min=c["min_us"] and round(c["min_us"] / 1000, 2),
                                           max=round(c["max_us"] / 1000, 2),
                                           mittel=round(c["sum_us"] / c["n"] / 1000, 2) if c["n"] else None))
        return dict(run=self.dir.name, start=self.start, dauer_s=round(self.t(), 1), port=self.port, pico=self.info,
                    verbindungen=self.connects, zeilen=self.lines, fehlerhafte_zeilen=self.bad,
                    stream_luecken=self.gaps, max_luecke_s=round(self.gap_max, 3), vbus_ausfaelle=self.vbus_lost,
                    health={k: v for k, v in self.rng.items()}, marker=self.marks, kanaele=kan,
                    schlaege=dict(ok=self.punches[1], verworfen=self.punches[0], max_km_h=round(self.v_max * 3.6, 1),
                                  mittel_km_h=round(self.v_sum / self.punches[1] * 3.6, 1) if self.punches[1] else None))

    def flush(self, force=False):
        if force or time.monotonic() >= self.next_sum:
            self.next_sum = time.monotonic() + 5
            (self.dir / "summary.json").write_text(json.dumps(self.summary(), indent=1, ensure_ascii=False),
                                                   encoding="utf-8")

    def close(self):
        self.note("ende")
        self.flush(True)
        for f in (self.raw, self._ev, self._he, self._pu):
            f.close()
