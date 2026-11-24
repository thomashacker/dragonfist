"""FAUSTREGEN: jeder Schlag hebt die Ente, dazwischen sinkt sie im Zieltakt. Der Takt wird stetig schneller."""
import math
import random

import pygame

from modi import ROT, Spiel, _zeit
from scenes import L, BG, INK, DIM, LO, GREEN
from training import Stats, auswerten, mmss

START, ANSTIEG, MAX = 1.0, 0.025, 4.0     # Schläge/s, +0,25 alle 10 s, Erkennung ist bis 4/s geprüft
HUB, FEDER, BAND = 0.15, 0.08, 0.4         # Höhe pro Schlag, Zug zur Mitte, sicherer Bereich (Höhe -1 … 1)
LUFT_AB, LUFT_AUF = 0.3, 0.2               # pro Sekunde außerhalb / innerhalb
TOENE = 9                                  # Takt-Ton folgt der Höhe in so vielen Stufen
PIX = 6                                    # Kantenlänge eines Szenen-Pixels


def ziel(t):
    return min(MAX, START + ANSTIEG * t)


def takt(ts, now, n=5):
    """Schläge pro Sekunde aus den letzten Abständen; bleibt man stehen, fällt der Wert mit der Pause."""
    ts = ts[-n:]
    if len(ts) < 2:
        return 0.0
    r = (len(ts) - 1) / max(ts[-1] - ts[0], 1e-3)
    pause = now - ts[-1]
    return min(r, 1 / pause) if pause > 1 / r else r


class Faustregen(Spiel):
    sounds = ("verbunden", "getrennt")          # nur der Takt-Ton spricht, die Schläge spürt man selbst

    def __init__(self, app, rnd=None):
        super().__init__(app)
        self.rnd = rnd or random.Random()
        self.phase, self.t0, self.start, self.t_aus, self.t_last = "warten", None, None, None, None
        self.ts, self.luft, self.tick_t, self.warn, self.hoehe = [], 1.0, None, 1.0, 0.0
        self.ziel, self.rate, self.ey, self.tropfen, self.regen_s = START, 0.0, None, [], 0.0
        self.blitz, self.blitz_bis, self.blitz_t = None, 0.0, 0.0

    def punch(self, r):
        if self.phase in ("warten", "laeuft") and r["ok"]:
            if self.phase == "warten":
                self.phase, self.start = "laeuft", _zeit(r)
                self.app.play("los")
            self.ts.append(_zeit(r))
            self.punches.append(r | {"t": _zeit(r) - self.start})
            self.hoehe = min(1.0, self.hoehe + HUB)

    def sicher(self):
        return abs(self.hoehe) <= BAND

    def schritt(self, now):
        dt, self.t_last = now - (self.t_last or now), now
        if self.tick_t is None or now >= self.tick_t:                   # Tonhöhe des Takts = Höhe der Ente
            self.tick_t = (self.tick_t or now) + 1 / self.ziel
            self.app.play(f"takt{round((self.hoehe + 1) / 2 * (TOENE - 1))}")
        if self.phase == "laeuft":
            t = now - self.start
            self.ziel, self.rate = ziel(t), takt(self.ts, now)
            self.hoehe = max(-1.0, self.hoehe - HUB * self.ziel * dt - FEDER * self.hoehe * dt)
            if self.sicher():
                self.luft = min(1.0, self.luft + LUFT_AUF * dt)
            else:
                self.luft -= LUFT_AB * dt
            for stufe in (0.35, 0.15):
                if self.luft < stufe <= self.warn:
                    self.app.play("fehl")
            self.warn = self.luft
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
        im = abs(self.rate / self.ziel - 1) <= 0.2
        t = (self.t_aus or now) - (self.start or now)
        y = L.y(90)
        f.text(s, f"ZIEL {self.ziel:.2f}/s", (40, y), "m", INK, "midleft")
        f.text(s, mmss(t), (L.W // 2, y), "m", INK, "center")
        f.text(s, f"DU {self.rate:.2f}/s", (L.W - 40, y), "m", GREEN if im else ROT, "midright")
        self.glas(s, g, now, dt)
        if self.phase == "warten":
            f.text(s, "LOS MIT DEM ERSTEN SCHLAG", (g.centerx, g.y + 110), "m", INK, "center")
            f.text(s, "jeder Schlag hebt die Ente  ·  im Takt schwimmt sie", (L.W // 2, g.y + 150), "s", DIM, "center")
            f.text(s, "tiefer Ton: schneller  ·  hoher Ton: langsamer", (L.W // 2, g.y + 180), "s", DIM, "center")
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
        hell = self.gewitter(now, w, oben)
        hell and lo.fill((18, 18, 18))
        for k in range(5):
            pygame.draw.ellipse(lo, DIM if hell else LO, (w * k // 5 - 2, 1 + 2 * (k % 2), w // 5 + 6, 8))
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
        soll = max(20.0, oben - self.hoehe * spiel - len(ENTE) + 3)                 # oben bleibt Platz für den Blitz
        self.ey = soll if self.ey is None else self.ey + (soll - self.ey) * min(1.0, dt * 5)
        y = round(self.ey + 0.6 * math.sin(now * 4))
        farbe = GREEN if abs(self.hoehe) <= BAND * 0.6 else INK if self.sicher() else ROT
        lo.blit(ente(farbe), (w // 2 - len(ENTE[0]) // 2, y))
        if y > oben + 2:
            for k in range(3):
                lo.set_at((w // 2 - 7 + 2 * k, y - 2 - int(now * 12 + k * 4) % 10), INK)
        if hell:
            pygame.draw.lines(lo, DIM, False, self.blitz, 3)
            pygame.draw.lines(lo, INK, False, self.blitz)
        s.blit(pygame.transform.scale(lo, (w * PIX, h * PIX)), g.topleft)
        pygame.draw.rect(s, LO, (g.x, g.y, w * PIX, h * PIX), 2)

    def gewitter(self, now, w, oben):
        """Blitze aus den Wolken; ist die Ente zu schnell oben, schlagen sie oft und auf sie zu."""
        if now >= self.blitz_t:
            hoch = self.hoehe > BAND
            self.blitz_t = now + (self.rnd.uniform(0.5, 1.0) if hoch else self.rnd.uniform(2.5, 5.0))
            x = w // 2 + self.rnd.randint(-3, 3) if hoch else self.rnd.randrange(4, w - 4)
            ende = round(self.ey) + 4 if hoch and self.ey is not None else self.rnd.randint(oben // 3, oben // 2)
            self.blitz, y = [(x, 9)], 9
            while y < ende:
                y = min(ende, y + self.rnd.randint(2, 4))
                x += self.rnd.choice((-2, -1, 1, 2))
                self.blitz.append((x, y))
            self.blitz_bis = now + 0.12
        return now < self.blitz_bis and len(self.blitz) > 1


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
