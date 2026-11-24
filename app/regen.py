"""FAUSTREGEN: einen Schlagtakt halten, der alle paar Sekunden schneller wird. Die Ente zeigt, ob man im Takt ist."""
import math
import random

import pygame

from modi import COUNTDOWN, ROT, Setup, Spiel, _zeit
from scenes import L, BG, INK, DIM, LO, GREEN
from training import Stats, auswerten, mmss

SCHRITT, STUFE_S, MAX = 0.25, 10, 4.0     # Ziel steigt alle 10 s um 0,25 Schläge/s, Erkennung ist bis 4/s geprüft
TOL, SPANNE = 0.2, 0.6                     # ±20 % gilt, ±60 % ist ganz oben/unten im Glas
LUFT_AB, LUFT_AUF, GNADE = 0.3, 0.2, 4.0   # pro Sekunde außerhalb / innerhalb, keine Strafe in den ersten Sekunden
PIX = 6                                    # Kantenlänge eines Szenen-Pixels


def ziel(t, start):
    return min(MAX, start + SCHRITT * int(t // STUFE_S))


def takt(ts, now, n=5):
    """Schläge pro Sekunde aus den letzten Abständen; bleibt man stehen, fällt der Wert mit der Pause."""
    ts = ts[-n:]
    if len(ts) < 2:
        return 0.0
    r = (len(ts) - 1) / max(ts[-1] - ts[0], 1e-3)
    pause = now - ts[-1]
    return min(r, 1 / pause) if pause > 1 / r else r


class Faustregen(Spiel):
    def __init__(self, app, start=1.0, hilfe=True, rnd=None):
        super().__init__(app)
        self.f0, self.hilfe, self.rnd = start, hilfe, rnd or random.Random()
        self.phase, self.t0, self.start, self.t_aus, self.t_last = "countdown", None, None, None, None
        self.ts, self.luft, self.stufe, self.t_stufe, self.tick_t = [], 1.0, 0, -9.0, None
        self.ziel, self.rate, self.ey, self.tropfen, self.regen_s = start, 0.0, None, [], 0.0

    def punch(self, r):
        if self.phase == "laeuft" and r["ok"]:
            self.ts.append(_zeit(r))
            self.punches.append(r | {"t": _zeit(r) - self.start})

    def abweichung(self):
        return self.rate / self.ziel - 1

    def schritt(self, now):
        dt, self.t_last = now - (self.t_last or now), now
        if self.phase == "countdown":
            n = COUNTDOWN - int(now - self.t0)
            if n > 0:
                return self.ton(n)
            self.phase, self.start, self.tick_t = "laeuft", now, now
            self.app.play("los")
        if self.phase == "laeuft":
            t = now - self.start
            stufe = int(t // STUFE_S)
            if stufe != self.stufe and ziel(t, self.f0) > self.ziel:
                self.t_stufe = now
                self.app.play("los")
            self.stufe, self.ziel, self.rate = stufe, ziel(t, self.f0), takt(self.ts, now)
            if abs(self.abweichung()) <= TOL:
                self.luft = min(1.0, self.luft + LUFT_AUF * dt)
            elif t > GNADE:
                self.luft -= LUFT_AB * dt
            if self.hilfe and now >= self.tick_t:
                self.tick_t += 1 / self.ziel
                self.app.play("tick")
            if self.luft <= 0:
                self.phase, self.t_aus, self.luft = "aus", now, 0.0
                self.app.play("ende")
        elif self.phase == "aus" and now - self.t_aus > 1.5:
            dauer = self.t_aus - self.start
            st = auswerten(self.punches, dauer) | dict(disz="FAUSTREGEN", ziel=round(self.ziel, 2))
            self.app.replace(Stats(self.app, st), 0.4)

    def draw(self, s, now):
        if self.t0 is None:
            self.t0 = now
        dt = now - (self.t_last or now)
        self.schritt(now)
        f = self.app.font
        f.text(s, "FAUSTREGEN", (L.W // 2, L.y(40)), "l", INK, "center")
        g = pygame.Rect(40, L.y(130), L.W - 80, L.H - L.y(130) - 110)
        if self.phase == "countdown":
            f.text(s, str(max(1, COUNTDOWN - int(now - self.t0))), g.center, "xl", INK, "center")
            f.text(s, "Halte den Takt, die Ente muss schwimmen", (L.W // 2, g.centery + 90), "s", DIM, "center")
            f.text(s, f"Start  {self.f0:g} Schläge pro Sekunde", (L.W // 2, g.centery + 130), "s", DIM, "center")
            return
        im = abs(self.abweichung()) <= TOL
        t = (self.t_aus or now) - self.start
        y = L.y(90)
        f.text(s, f"ZIEL {self.ziel:.2f}/s", (40, y), "m", INK, "midleft")
        f.text(s, mmss(t), (L.W // 2, y), "m", INK, "center")
        f.text(s, f"DU {self.rate:.2f}/s", (L.W - 40, y), "m", GREEN if im else ROT, "midright")
        self.glas(s, g, now, dt)
        if now - self.t_stufe < 1.5:
            f.text(s, f"SCHNELLER!  {self.ziel:.2f}/s", (g.centerx, g.y + 110), "l", GREEN, "center")
        if self.phase == "aus":
            f.text(s, "ABGESOFFEN", (g.centerx, g.y + 110), "xl", ROT, "center")
        b = pygame.Rect(150, L.H - 74, L.W - 190, 18)
        f.text(s, "LUFT", (40, b.centery), "s", DIM, "midleft")
        pygame.draw.rect(s, LO, b, 1)
        col = GREEN if self.luft > 0.5 else INK if self.luft > 0.25 else ROT
        pygame.draw.rect(s, col, (b.x, b.y, int(b.w * self.luft), b.h))
        f.text(s, "ZURÜCK  abbrechen", (L.W // 2, L.H - 18), "xs", DIM, "center")

    def glas(self, s, g, now, dt):
        """Szene in grober Auflösung zeichnen und ohne Glättung hochskalieren: alles im selben Pixelraster."""
        lo = pygame.Surface((g.w // PIX, g.h // PIX))
        w, h = lo.get_size()
        oben, spiel = h // 2 + 5, h // 2 - 10
        for k in range(5):
            pygame.draw.ellipse(lo, LO, (w * k // 5 - 2, 1 + 2 * (k % 2), w // 5 + 6, 8))
        self.regen_s += dt * self.ziel * 8
        while self.regen_s >= 1:
            self.regen_s -= 1
            self.tropfen.append([self.rnd.randrange(2, w - 2), 9.0])
        for tr in self.tropfen:
            tr[1] += 90 * dt
            lo.fill(DIM, (tr[0], int(tr[1]), 1, 2))
        self.tropfen = [tr for tr in self.tropfen if tr[1] < oben]
        for x in range(w):
            y = oben + round(math.sin(x / 5 + now * 3))
            lo.fill(LO, (x, y, 1, h - y))
            lo.set_at((x, y), DIM)
            if (x * 7 + int(now * 6)) % 11 == 0:
                lo.set_at((x, y + 3 + x % 4 * 3), DIM)
        d = self.abweichung()
        raus = min(1.0, max(0.0, abs(d) - TOL) / (SPANNE - TOL))        # im Bereich: Ente sitzt auf dem Wasser
        soll = oben - math.copysign(raus, d) * spiel - len(ENTE) + 3
        self.ey = soll if self.ey is None else self.ey + (soll - self.ey) * min(1.0, dt * 5)
        y = round(self.ey + 0.6 * math.sin(now * 4))
        lo.blit(ente(GREEN if abs(d) <= TOL else ROT), (w // 2 - len(ENTE[0]) // 2, y))
        if y > oben:
            for k in range(3):
                lo.set_at((w // 2 - 7 + 2 * k, y - 2 - int(now * 12 + k * 4) % 10), INK)
        s.blit(pygame.transform.scale(lo, (w * PIX, h * PIX)), g.topleft)
        pygame.draw.rect(s, LO, (g.x, g.y, w * PIX, h * PIX), 2)


ENTE = ("....XXX.........",
        "...XXXXX........",
        "..BBXOXXX.......",
        ".BBBXXXXX.......",
        "...XXXXX........",
        "....XXXX....X...",
        "..XXXXXXXXXXXX..",
        ".XXXXXXXXXXXXXX.",
        ".XXXXWWWWWWXXXX.",
        ".XXXXXWWWWXXXXX.",
        "..XXXXXXXXXXXX..",
        "...XXXXXXXXXX...")
_enten = {}


def ente(farbe):
    if farbe not in _enten:
        img = pygame.Surface((len(ENTE[0]), len(ENTE)), pygame.SRCALPHA)
        pal = {"X": farbe, "W": tuple(c // 2 for c in farbe), "B": INK, "O": BG}
        for y, zeile in enumerate(ENTE):
            for x, c in enumerate(zeile):
                c in pal and img.set_at((x, y), pal[c])
        _enten[farbe] = img
    return _enten[farbe]


def faustregen(app):
    return Setup(app, "FAUSTREGEN", [("START-TAKT", "regen_start", (0.5, 1.0, 1.5, 2.0), " /s"),
                                     ("TAKT-HILFE", "regen_hilfe", ("AN", "AUS"), "")],
                 lambda app, start, hilfe: Faustregen(app, start, hilfe == "AN"))
