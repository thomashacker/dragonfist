"""FAUSTREGEN: jeder Schlag hebt die Ente, sie sinkt im Zieltakt, der stetig schneller wird. Nur zu langsam ist schlecht."""
import math
import random

import pygame

from modi import ROT, Spiel, _zeit
from scenes import L, BG, INK, DIM, LO, GREEN
from training import Stats, auswerten, mmss

START, ANSTIEG = 1.0, 0.025                # Schläge/s, +0,25 alle 10 s, ohne Obergrenze
HUB, BAND = 0.15, 0.4                      # Höhe pro Schlag (-1 … 1), unter -BAND geht die Luft aus
LUFT_AB, LUFT_AUF = 0.3, 0.2               # pro Sekunde unter / über der Grenze
FENSTER = 3.0                              # s, über die der eigene Takt gemittelt wird
PIX = 6                                    # Kantenlänge eines Szenen-Pixels


def ziel(t):
    return START + ANSTIEG * t


def takt(ts, now, start):
    """Schläge pro Sekunde in den letzten Sekunden; fällt nicht auf 0, nur weil die Hand gerade zurück ist."""
    fenster = min(FENSTER, max(1.0, now - start))
    return sum(now - t <= fenster for t in ts[-64:]) / fenster


class Faustregen(Spiel):
    sounds = ("verbunden", "getrennt")          # nur der Takt spricht, die Schläge spürt man selbst

    @property
    def leds(self):
        return "spiel" if self.phase == "aus" else "welle"

    def welle(self):
        """Lauflicht an der Kiste: wandert im Zieltakt, Farbe wie die Ente."""
        farbe = (0, 255, 0) if self.hoehe >= 0 else (255, 255, 255) if self.sicher() else (255, 0, 0)
        return int(round(1000 / self.ziel, -1)), farbe

    def __init__(self, app, rnd=None):
        super().__init__(app)
        self.rnd = rnd or random.Random()
        self.phase, self.t0, self.start, self.t_aus, self.t_last = "warten", None, None, None, None
        self.ts, self.luft, self.tick_t, self.hoehe = [], 1.0, None, 0.0
        self.ziel, self.rate, self.ey, self.tropfen, self.regen_s = START, 0.0, None, [], 0.0
        self.blitz, self.blitz_bis, self.blitz_t = None, 0.0, 0.0

    def punch(self, r):
        if self.phase in ("warten", "laeuft") and r["ok"]:
            if self.phase == "warten":
                self.phase, self.start = "laeuft", _zeit(r)
            self.ts.append(_zeit(r))
            self.punches.append(r | {"t": _zeit(r) - self.start})
            self.hoehe = min(1.0, self.hoehe + HUB)

    def sicher(self):
        return self.hoehe >= -BAND

    def schritt(self, now):
        dt, self.t_last = now - (self.t_last or now), now
        if self.phase != "aus" and (self.tick_t is None or now >= self.tick_t):
            self.tick_t = (self.tick_t or now) + 1 / self.ziel
            self.app.play("takt" if self.hoehe >= 0 else "takt_nass")
        if self.phase == "laeuft":
            t = now - self.start
            self.ziel, self.rate = ziel(t), takt(self.ts, now, self.start)
            self.hoehe = max(-1.0, self.hoehe - HUB * self.ziel * dt)          # sinkt im Zieltakt, Schläge heben
            if self.sicher():
                self.luft = min(1.0, self.luft + LUFT_AUF * dt)
            else:
                self.luft -= LUFT_AB * dt
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
        t = (self.t_aus or now) - (self.start or now)
        y = L.y(90)
        f.text(s, f"ZIEL {self.ziel:.2f}/s", (40, y), "m", INK, "midleft")
        f.text(s, mmss(t), (L.W // 2, y), "m", INK, "center")
        if self.phase != "warten":
            col = GREEN if self.rate >= self.ziel else INK if self.rate >= 0.85 * self.ziel else ROT
            f.text(s, f"DU {self.rate:.2f}/s", (L.W - 40, y), "m", col, "midright")
        self.glas(s, g, now, dt)
        if self.phase == "aus":
            f.text(s, "ABGESOFFEN", (g.centerx, g.y + 110), "xl", ROT, "center")
        b = pygame.Rect(150, L.H - 74, L.W - 190, 18)
        f.text(s, "LUFT", (40, b.centery), "s", DIM, "midleft")
        pygame.draw.rect(s, LO, b, 1)
        col = GREEN if self.luft > 0.5 else INK if self.luft > 0.25 else ROT
        pygame.draw.rect(s, col, (b.x, b.y, int(b.w * self.luft), b.h))

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
        farbe = GREEN if self.hoehe >= 0 else INK if self.sicher() else ROT
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
        if now >= self.blitz_t:
            self.blitz_t = now + self.rnd.uniform(2.5, 5.0)
            x, ende = self.rnd.randrange(4, w - 4), self.rnd.randint(oben // 3, oben // 2)
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
