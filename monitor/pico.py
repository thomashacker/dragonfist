"""Verbindung zum Pico: Kanäle, Zeilenprotokoll, Zustand der Schlag-Logik, serieller Leser."""
import collections
import threading
import time

import serial
from serial.tools import list_ports

from punch import Punch, DEAD_S

A = (0, 3, 6, 9, 12, 15)
B = (28, 27, 22, 21, 14, 18, 17)
GP = A + B
NAME = [f"A{i + 1}" for i in range(len(A))] + [f"B{i + 1}" for i in range(len(B))]



class Kanal:
    __slots__ = ("v", "seen0", "breaks", "t")

    def __init__(self):
        self.v, self.seen0, self.breaks, self.t = None, False, 0, 0.0

    def dead(self, now):
        return self.v == 0 and now - self.t > DEAD_S


class State:
    def __init__(self, runlog=None, dist_mm=200):
        self.lock = threading.Lock()
        self.punch = Punch(len(A), len(GP), dist_mm)
        self.reset()
        self.port = None
        self.health = {}
        self.info = None
        self.rx = collections.deque(maxlen=400)
        self.rl = runlog
        self.mark = (0, 0.0)
        self.sfx = collections.deque(maxlen=32)
        self.hits = collections.deque(maxlen=16)
        self.leds = collections.deque(maxlen=32)
        self.out = collections.deque(maxlen=16)

    def connect(self, port):
        with self.lock:
            if bool(port) != bool(self.port):
                self.sfx.append("verbunden" if port else "getrennt")
            if port:
                self.reset()
            self.port = port
            if self.rl:
                if port:
                    self.rl.connect(port)
                else:
                    self.rl.note("disconnect")

    def marker(self):
        with self.lock:
            if self.rl:
                self.mark = (self.rl.mark(), time.monotonic())

    def note(self, s):
        with self.lock:
            self.rl and self.rl.note(s)

    def reset(self):
        self.ch = [Kanal() for _ in GP]
        self.punch.reset()
        self.log = collections.deque(maxlen=12)

    def feed(self, line):
        p = line.split()
        if not p:
            return
        now = time.monotonic()
        with self.lock:
            rl = self.rl
            try:
                self.rx.append(now)
                if p[0] == "S":
                    m = int(p[1], 16)
                    for i, c in enumerate(self.ch):
                        v = m >> i & 1
                        if c.v != v:
                            c.v, c.t = v, now
                        c.seen0 |= not v
                    rl and rl.status(now, m)
                    self.punch.status(m, now)
                elif p[0] == "E":
                    i, v, tus = int(p[1]), int(p[2]), int(p[3])
                    c = self.ch[i]
                    if c.v == 1 and v == 0:
                        c.breaks += 1
                    if c.v != v:
                        self.sfx.append("frei" if v else "bruch")
                    c.v, c.t = v, now
                    c.seen0 |= not v
                    self.punch.edge(i, v, tus, now)
                    self.log.appendleft((time.time(), i, v, rl.event(i, v, tus) if rl else None))
                elif p[0] == "H":
                    self.health = dict(vbus=int(p[1]), vsys=int(p[2]) / 1000, temp=int(p[3]) / 10,
                                       scan=int(p[4]), up=int(p[5]) / 1000)
                    rl and rl.health(self.health)
                elif p[0] == "I":
                    self.info = dict(ver=int(p[1]), uid=p[2])
                    if rl:
                        rl.info = self.info
                else:
                    raise ValueError
                rl and rl.line(line.strip())
            except (ValueError, IndexError):
                rl and rl.line(line.strip(), ok=False)

    def tick(self, now):
        with self.lock:
            self.punch.set_dead(sum(c.dead(now) << i for i, c in enumerate(self.ch)), now)
            for r in self.punch.tick(now):
                self.hits.append(r)
                self.rl and self.rl.punch(r)
            for k, hand in self.punch.events:
                self.sfx.append(k)
                self.leds.append((k, hand))
            self.punch.events.clear()
            self.rl and self.rl.flush()

    def send(self, cmd):
        with self.lock:
            self.out.append(cmd)

    def rate(self, now):
        return sum(1 for t in self.rx if now - t < 1)

    def live(self, now):
        return bool(self.rx) and now - self.rx[-1] < 1.5


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:
            return p.device


STILL_S = 3                 # so lange ohne Zeile -> Pico anstoßen
WECKEN = b"\r\x03\x03\x02\x04"   # Strg-C ×2 (aus REPL/hängendem Code), Strg-B, Strg-D = main.py neu starten


def reader(st, port, stop, still=STILL_S):
    while not stop.is_set():
        dev = port or find_port()
        if dev:
            try:
                with serial.Serial(dev, 115200, timeout=0.05) as s:
                    st.connect(dev)
                    zuletzt, stoesse, buf = time.monotonic(), 0, b"\n"
                    while not stop.is_set():
                        while st.out:
                            s.write(st.out.popleft().encode() + b"\n")
                        line = s.readline()
                        now = time.monotonic()
                        if line:
                            buf = line if buf.endswith(b"\n") or len(buf) > 256 else buf + line
                            if buf.endswith(b"\n"):
                                st.feed(buf.decode("ascii", "ignore"))
                            zuletzt, stoesse = now, 0
                        elif now - zuletzt > still:
                            if stoesse == 2:
                                break                      # zweimal ohne Erfolg -> Port neu öffnen
                            s.write(WECKEN)
                            zuletzt, stoesse = now, stoesse + 1
            except (serial.SerialException, OSError):
                pass
            if st.port:
                st.connect(None)
        stop.wait(1)
