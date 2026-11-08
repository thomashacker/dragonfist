import argparse
import collections
import os
import random
import threading
import time
from pathlib import Path

import pygame
import serial
from serial.tools import list_ports

from punch import Punch
from runlog import RunLog, GLITCH_US
from sound import Sfx

W, H = 1024, 600
A = (0, 3, 6, 9, 12, 15)
B = (28, 27, 26, 21, 20, 18, 17)
GP = A + B
NAME = [f"A{i + 1}" for i in range(len(A))] + [f"B{i + 1}" for i in range(len(B))]
MA_PAIR = 21

WHITE, GREY, DIM, BLACK = (235, 235, 235), (120, 120, 120), (50, 50, 50), (0, 0, 0)
GREEN = (90, 230, 130)


class Kanal:
    __slots__ = ("v", "seen0", "breaks", "t")

    def __init__(self):
        self.v, self.seen0, self.breaks, self.t = None, False, 0, 0.0


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

    def reset(self):
        self.ch = [Kanal() for _ in GP]
        self.punch.low, self.punch.ph = 0, None
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
            r = self.punch.tick(now)
            if r:
                r["ok"] and self.sfx.append("treffer")
                self.rl and self.rl.punch(r)

    def rate(self, now):
        return sum(1 for t in self.rx if now - t < 1)

    def live(self, now):
        return bool(self.rx) and now - self.rx[-1] < 1.5


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:
            return p.device


def reader(st, port, stop):
    while not stop.is_set():
        dev = port or find_port()
        if dev:
            try:
                with serial.Serial(dev, 115200, timeout=0.2) as s:
                    st.connect(dev)
                    while not stop.is_set():
                        line = s.readline()
                        if line:
                            st.feed(line.decode("ascii", "ignore"))
            except serial.SerialException:
                pass
            if st.port:
                st.connect(None)
        stop.wait(1)


def demo(st, stop):
    st.connect("DEMO")
    v = [1] * len(GP)
    for i in (9, 11, 12):
        v[i] = None
    t0 = time.monotonic()
    nxt = [t0 + random.uniform(0.5, 4) for _ in GP]
    th = 0
    while not stop.wait(0.05):
        now = time.monotonic()
        for i in range(len(GP)):
            if v[i] is not None and now > nxt[i]:
                v[i] ^= 1
                st.feed(f"E {i} {v[i]} {int(now * 1e6) & 0x3FFFFFFF}")
                nxt[i] = now + (random.uniform(0.08, 0.3) if v[i] == 0 else random.uniform(1, 6))
            elif v[i] == 1 and random.random() < 0.002:
                tus = int(now * 1e6) & 0x3FFFFFFF
                st.feed(f"E {i} 0 {tus}")
                st.feed(f"E {i} 1 {tus + 1400}")
        st.feed("S %x" % sum((1 if x is None else x) << i for i, x in enumerate(v)))
        if now - th > 0.5:
            th = now
            st.feed(f"H 1 {4880 + random.randint(-15, 15)} {312 + random.randint(-3, 3)} 84120 {int((now - t0) * 1000)}")
            st.feed("I 1 e6614c311b4a2f2c 6 7")


class Ui:
    def __init__(self, surf):
        self.s = surf
        self.mute = False
        mono = "consolas,dejavusansmono,liberationmono,couriernew"
        self.f = {k: pygame.font.SysFont(mono, n, bold=k in ("l", "xl")) for k, n in
                  (("xs", 12), ("s", 15), ("m", 20), ("l", 28), ("xl", 40))}

    def text(self, t, pos, size="s", col=WHITE, anchor="topleft"):
        img = self.f[size].render(t, True, col)
        r = img.get_rect(**{anchor: pos})
        self.s.blit(img, r)
        return r

    def box(self, r, col=WHITE, fill=None):
        if fill:
            pygame.draw.rect(self.s, fill, r)
        pygame.draw.rect(self.s, col, r, 1)

    def beam(self, cx, cy, state, col):
        x0, x1 = cx - 42, cx + 42
        pygame.draw.rect(self.s, col, (x0 - 6, cy - 6, 12, 12), 2)
        pygame.draw.circle(self.s, col, (x1, cy), 7, 2)
        if state == "ok":
            pygame.draw.line(self.s, col, (x0 + 8, cy), (x1 - 9, cy), 2)
            for k in range(3):
                x = x0 + 18 + k * 18 + int(time.monotonic() * 40) % 18
                pygame.draw.line(self.s, col, (x, cy - 3), (x + 4, cy), 2)
                pygame.draw.line(self.s, col, (x, cy + 3), (x + 4, cy), 2)
        elif state == "bruch":
            pygame.draw.line(self.s, col, (x0 + 8, cy), (cx - 10, cy), 2)
            pygame.draw.line(self.s, col, (cx - 5, cy - 6), (cx + 5, cy + 6), 2)
            pygame.draw.line(self.s, col, (cx - 5, cy + 6), (cx + 5, cy - 6), 2)
        else:
            for x in range(x0 + 10, x1 - 10, 8):
                pygame.draw.line(self.s, col, (x, cy), (x + 3, cy), 1)

    def icon(self, kind, x, y, col=WHITE):
        d = self.s
        if kind == "usb":
            pygame.draw.rect(d, col, (x, y + 4, 10, 8), 2)
            pygame.draw.line(d, col, (x + 10, y + 8), (x + 16, y + 8), 2)
        elif kind == "volt":
            pygame.draw.lines(d, col, False, [(x + 9, y), (x + 3, y + 9), (x + 11, y + 9), (x + 5, y + 16)], 2)
        elif kind == "temp":
            pygame.draw.rect(d, col, (x + 5, y, 6, 11), 2)
            pygame.draw.circle(d, col, (x + 8, y + 13), 4, 2)
        elif kind == "scan":
            pygame.draw.rect(d, col, (x + 3, y + 3, 10, 10), 2)
            for k in (5, 8, 11):
                pygame.draw.line(d, col, (x + k, y), (x + k, y + 2))
                pygame.draw.line(d, col, (x + k, y + 14), (x + k, y + 16))
        elif kind == "link":
            pygame.draw.circle(d, col, (x + 4, y + 8), 4, 2)
            pygame.draw.circle(d, col, (x + 12, y + 8), 4, 2)
        elif kind == "amp":
            pygame.draw.circle(d, col, (x + 8, y + 8), 7, 2)
            pygame.draw.line(d, col, (x + 5, y + 11), (x + 11, y + 5), 2)
        elif kind == "eye":
            pygame.draw.ellipse(d, col, (x, y + 4, 16, 9), 2)
            pygame.draw.circle(d, col, (x + 8, y + 8), 2)

    def cell(self, r, i, c, now):
        if c.v == 0:
            state, fg, fill = "bruch", BLACK, WHITE
        elif c.v == 1 and c.seen0:
            state, fg, fill = "ok", WHITE, None
        else:
            state, fg, fill = "?", GREY, None
        self.box(r, WHITE if state != "?" else DIM, fill)
        self.text(NAME[i], (r.x + 10, r.y + 6), "l", fg)
        self.text(f"GP{GP[i]}", (r.right - 8, r.y + 10), "xs", fg if fill else GREY, "topright")
        self.beam(r.centerx, r.y + 64, state, fg)
        word = {"ok": "SIGNAL", "bruch": "UNTERBROCHEN", "?": "UNGEPRÜFT"}[state]
        self.text(word, (r.centerx, r.y + 88), "s", fg, "midtop")
        self.text(f"BR {c.breaks}", (r.x + 10, r.bottom - 22), "xs", fg)

    def punch_box(self, r, last, n, best, armed, now):
        fresh = last and now - last["t"] < 3
        self.box(r, WHITE if fresh else DIM)
        self.text(f"SCHLAG #{n}", (r.x + 10, r.y + 8), "xs", GREY)
        if armed:
            msg, col = "MESSE …", WHITE
        elif last:
            msg, col = last["msg"], (GREEN if last["ok"] else GREY) if fresh else DIM
        else:
            msg, col = "BEREIT", GREY
        self.text(msg, (r.centerx, r.y + 28), "s", col, "midtop")
        v = last if last and last["ok"] else None
        self.text(f"{v['v'] * 3.6:.1f}" if v else "–", (r.centerx, r.y + 52), "xl", GREEN if v and fresh else WHITE,
                  "midtop")
        self.text("km/h", (r.centerx, r.y + 96), "s", GREY, "midtop")
        if v:
            self.text(f"{v['v']:.2f} m/s · {v['dt'] / 1000:.1f} ms", (r.centerx, r.y + 114), "xs", GREY, "midtop")
        self.text(f"MAX {best * 3.6:.1f}", (r.centerx, r.bottom - 18), "xs", GREY, "midtop")

    def draw(self, st, now):
        d = self.s
        d.fill(BLACK)
        with st.lock:
            ch, health, info, log = list(st.ch), dict(st.health), st.info, list(st.log)
            pu = st.punch
            last, n, best, armed = pu.last, pu.n, pu.best, pu.ph
            live, rate, port, (mk, mk_t) = st.live(now), st.rate(now), st.port, st.mark
            run = st.rl.dir.name if st.rl else None
        self.text("DRAGONFIST", (24, 10), "l")
        self.text("// SENSOR MONITOR", (220, 18), "s", GREY)
        status = f"LIVE  {port}" if live else (f"KEINE DATEN  {port}" if port else "SUCHE PICO …")
        r = self.text(status, (W - 24, 18), "s", WHITE if live else GREY, "topright")
        self.icon("link", r.x - 24, 17, WHITE if live else GREY)
        if run:
            r = self.text(f"REC {run}" + (f"  M{mk}" if mk else ""), (r.x - 40, 19), "xs", GREY, "topright")
            if int(now * 2) % 2:
                pygame.draw.circle(d, WHITE, (r.x - 10, 26), 4)
        if mk and now - mk_t < 2:
            self.text(f"MARKER {mk}", (W // 2, 18), "m", WHITE, "midtop")
        pygame.draw.line(d, DIM, (24, 50), (W - 24, 50))

        cw, gap = 132, 8
        for row, (titel, idx, y) in enumerate((("EBENE A · VORNE", range(len(A)), 60),
                                                ("EBENE B · HINTEN", range(len(A), len(GP)), 232))):
            self.text(titel, (24, y), "xs", GREY)
            for k, i in enumerate(idx):
                self.cell(pygame.Rect(24 + k * (cw + gap), y + 18, cw, 148), i, ch[i], now)

        self.punch_box(pygame.Rect(24 + len(A) * (cw + gap), 78, W - 48 - len(A) * (cw + gap), 148),
                       last, n, best, armed, now)

        hb = pygame.Rect(24, 408, 480, 166)
        self.box(hb, DIM)
        self.text("HEALTH", (hb.x + 12, hb.y + 8), "xs", GREY)
        erkannt = sum(c.seen0 for c in ch)
        rows = [("usb", "USB 5V", ("OK" if health.get("vbus") else "FEHLT") if health else "–"),
                ("volt", "VSYS", f"{health['vsys']:.2f} V" if health else "–"),
                ("temp", "TEMP", f"{health['temp']:.1f} °C" if health else "–"),
                ("scan", "SCAN", f"{health['scan'] / 1000:.1f} kHz" if health else "–"),
                ("link", "LINK", f"{rate} msg/s"),
                ("eye", "ERKANNT", f"{erkannt}/{len(GP)}"),
                ("amp", "STROM*", f"~{erkannt * MA_PAIR} mA"),
                ("scan", "UPTIME", time.strftime("%H:%M:%S", time.gmtime(health["up"])) if health else "–")]
        for k, (ic, lab, val) in enumerate(rows):
            x, y = hb.x + 14 + (k // 4) * 236, hb.y + 32 + (k % 4) * 34
            self.icon(ic, x, y + 2)
            self.text(lab, (x + 26, y + 3), "s", GREY)
            self.text(val, (x + 220, y), "m", WHITE, "topright")

        lb = pygame.Rect(520, 408, W - 544, 166)
        self.box(lb, DIM)
        self.text("EREIGNISSE", (lb.x + 12, lb.y + 8), "xs", GREY)
        for k, (t, i, v, dur) in enumerate(log[:8]):
            y = lb.y + 30 + k * 17
            col = WHITE if k == 0 else GREY
            self.text(time.strftime("%H:%M:%S", time.localtime(t)) + f".{int(t * 100) % 100:02d}", (lb.x + 12, y),
                      "s", col)
            self.text(NAME[i], (lb.x + 120, y), "s", col)
            self.text("▼ BRUCH" if v == 0 else "▲ FREI", (lb.x + 170, y), "s", col)
            if dur is not None:
                self.text(("! " if dur < GLITCH_US else "") + f"{dur / 1000:.1f} ms", (lb.right - 12, y), "s",
                          col, "topright")

        uid = f"PICO {info['uid']}  FW {info['ver']}" if info else ""
        keys = f"ESC ende · R reset · M marker · S ton {'aus' if self.mute else 'an'} · F vollbild"
        self.text(f"{uid}   * geschätzt   {keys}", (24, H - 16), "xs", DIM)

        if not live:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 190))
            d.blit(ov, (0, 0))
            msg = "PICO VERBUNDEN – KEINE DATEN" if port else "KEIN PICO GEFUNDEN"
            sub = "läuft main.py auf dem Pico?" if port else "USB-Kabel prüfen"
            self.text(msg, (W // 2, H // 2 - 24), "xl", WHITE, "center")
            self.text(sub, (W // 2, H // 2 + 20), "s", GREY, "center")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--shot")
    ap.add_argument("--runs", default=str(Path(__file__).resolve().parent.parent / "runs"))
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--mute", action="store_true")
    ap.add_argument("--abstand", type=float, default=200, help="mm zwischen Ebene A und B")
    a = ap.parse_args()
    if a.shot:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.mixer.pre_init(44100, -16, 1, 256)
    pygame.init()
    flags = pygame.SCALED | (pygame.FULLSCREEN if a.fullscreen else pygame.RESIZABLE)
    screen = pygame.display.set_mode((W, H), flags)
    pygame.display.set_caption("dragonfist monitor")
    rl = None if a.no_log else RunLog(a.runs, NAME, GP, "demo" if a.demo else "")
    ui, st, stop = Ui(screen), State(rl, a.abstand), threading.Event()
    sfx, ui.mute = Sfx(), a.mute or bool(a.shot)
    threading.Thread(target=demo if a.demo else reader, args=(st, stop) if a.demo else (st, a.port, stop),
                     daemon=True).start()

    clock, t_end = pygame.time.Clock(), time.monotonic() + (12 if a.demo else 4)
    try:
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q)):
                    return
                if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                    with st.lock:
                        st.reset()
                        st.punch.n, st.punch.best, st.punch.last = 0, 0.0, None
                        rl and rl.note("reset")
                if e.type == pygame.KEYDOWN and e.key == pygame.K_m:
                    st.marker()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                    ui.mute = not ui.mute
                if e.type == pygame.KEYDOWN and e.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
            st.tick(time.monotonic())
            with st.lock:
                q = list(st.sfx)
                st.sfx.clear()
            if not ui.mute:
                for k in dict.fromkeys(q):
                    sfx.play(k)
            now = time.monotonic()
            ui.draw(st, now)
            pygame.display.flip()
            if rl:
                with st.lock:
                    rl.flush()
            if a.shot and now > t_end:
                pygame.image.save(screen, a.shot)
                return
            clock.tick(60)
    finally:
        stop.set()
        if rl:
            with st.lock:
                rl.close()
            print(rl.dir)


if __name__ == "__main__":
    main()
