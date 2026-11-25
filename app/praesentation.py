"""Präsentation unter der Decke: Musik blendet ein, beim ersten Drop gehen die Lichter an, beim dritten wird enthüllt."""
import math
import random

import pygame

from scenes import L, ASSETS, BG, INK, Scene

DATEI = "praesentation.mp3"
EINBLENDEN_MS = 4000
DROPS = (28.0, 46.9, 65.6, 85.85, 90.0)      # Einsätze im Stück; der dritte ist die Enthüllung
ENTHUELLEN = DROPS[2]
AUSBLENDEN, ENDE = 99.5, 104.5
ABBRUCH_S = 1.2
FARBEN = ((255, 90, 0), (0, 120, 255), (90, 230, 130), (255, 0, 160), (255, 220, 0), (0, 230, 230))
BLITZ_S = 0.35
DREH_BLATT, SPALTEN, DREH_N = "logo3d.jpg", 12, 96     # gerendert mit cad/logo_drehung.py


def _hex(c, k=1.0):
    return "".join(f"{int(x * k):02x}" for x in c)


class Praesentation(Scene):
    bare, music, sounds, leds = True, False, (), "show"     # music False: Szene spielt selbst

    def __init__(self, app, rnd=None):
        super().__init__(app)
        self.rnd, self.t0, self.stopp, self.drop, self.konfetti = rnd or random.Random(), None, None, -1, []
        self.zeit_jetzt = 0.0
        self.n, self.cache = min(L.W, L.H) * 3 // 5, {}
        try:
            self.blatt = pygame.image.load(str(ASSETS / DREH_BLATT)).convert()
        except (pygame.error, FileNotFoundError):
            self.blatt = None
            logo = pygame.image.load(str(ASSETS / "vietvodao.png")).convert_alpha()
            self.logo = pygame.transform.smoothscale(logo, (self.n * 2 // 3, self.n * 2 // 3))
        self.spielt = False
        if not app.mute:
            try:
                pygame.mixer.music.load(str(ASSETS / "music" / DATEI))
                pygame.mixer.music.set_volume(app.cfg["volume"] / 100)
                pygame.mixer.music.play(0, fade_ms=EINBLENDEN_MS)
                self.spielt = True
            except (pygame.error, FileNotFoundError):
                pass

    def on(self, a):
        if a in ("ok", "back", "gelb") and self.stopp is None:
            self.stopp = self.zeit_jetzt
            self.spielt and pygame.mixer.music.fadeout(int(ABBRUCH_S * 1000))

    def u(self, now):
        if self.t0 is None:
            self.t0 = self.t_alt = now
        return now - self.t0

    def schluss(self, u):
        """0 = voll, 1 = schwarz: Ausblenden am Ende oder nach Abbruch."""
        if self.stopp is not None:
            return min(1.0, (u - self.stopp) / ABBRUCH_S)
        return min(1.0, max(0.0, (u - AUSBLENDEN) / (ENDE - AUSBLENDEN)))

    def licht(self, now):
        u = self.u(now)
        k = 1 - self.schluss(u)
        if u < DROPS[0]:
            return "L 000000 000000"
        seit = u - max(d for d in DROPS if d <= u)
        if seit < BLITZ_S:
            return "L " + " ".join([_hex((255, 255, 255), k)] * 2)
        if k < 1:
            return "L " + " ".join([_hex(FARBEN[0], k)] * 2)
        takt = int(u * 4)
        if u < DROPS[1]:
            return f"L {_hex(FARBEN[takt % 6])} {_hex(FARBEN[(takt + 3) % 6])}"
        if u < ENTHUELLEN:
            return "T" if int(u / 2) % 2 else f"W 120 {_hex(FARBEN[int(u / 2) % 6])}"
        if seit < 1.2:
            return "L ffffff ffffff" if int(seit * 16) % 2 else "L 000000 000000"
        return "T" if int(u / 3) % 3 else f"L {_hex(FARBEN[takt % 6])} {_hex(FARBEN[(takt + 2) % 6])}"

    def schuss(self, n):
        for _ in range(n):
            x = self.rnd.choice((0.0, 1.0)) if self.rnd.random() < 0.7 else self.rnd.random()
            w = math.radians(self.rnd.uniform(55, 80))
            v = self.rnd.uniform(1.3, 2.2) * L.H
            vx = v * math.cos(w) * (1 if x < 0.5 else -1)
            self.konfetti.append([x * L.W, L.H + 10, vx, -v * math.sin(w), self.rnd.choice(FARBEN),
                                  self.rnd.uniform(0, 6.3), self.rnd.uniform(-9, 9), self.rnd.uniform(5, 10)])

    def bewegen(self, dt):
        for p in self.konfetti:
            p[2] *= 1 - 1.2 * dt
            p[3] = p[3] * (1 - 2.4 * dt) + 0.6 * L.H * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[5] += p[6] * dt
        self.konfetti = [p for p in self.konfetti if p[1] < L.H + 20]

    def gedreht(self, w):
        """3D-Münze aus der gerenderten Bildfolge; ohne sie das flache Logo, Breite mit |cos|."""
        if self.blatt:
            i = round(w / (2 * math.pi) * DREH_N) % DREH_N
            img = self.cache.get(i)
            if img is None:
                px = self.blatt.get_width() // SPALTEN
                img = self.blatt.subsurface(((i % SPALTEN) * px, (i // SPALTEN) * px, px, px))
                if px != self.n:
                    img = pygame.transform.smoothscale(img, (self.n, self.n))
                self.cache[i] = img
            return img
        b = max(2, int(self.logo.get_width() * abs(math.cos(w))) // 4 * 4)
        img = self.cache.get(b)
        if img is None:
            img = self.cache[b] = pygame.transform.scale(self.logo, (b, self.logo.get_height()))
        return img

    def draw(self, s, now):
        u = self.u(now)
        dt = min(0.05, now - self.t_alt)
        self.t_alt, self.zeit_jetzt = now, u
        aus = self.schluss(u)
        if aus >= 1:
            self.app.volume()
            return self.app.pop()
        d = sum(x <= u for x in DROPS) - 1
        if d > self.drop:
            self.drop = d
            d >= 2 and self.schuss(260 if d == 2 else 140)
        if u >= ENTHUELLEN and self.stopp is None and int(u * 2) != int((u - dt) * 2) and self.rnd.random() < 0.6:
            self.schuss(25)
        self.bewegen(dt)
        if u < DROPS[0]:
            hell, w = min(1.0, u / DROPS[0]) * 0.35, u * 0.4
        elif u < ENTHUELLEN:
            hell, w = 0.6, (u - DROPS[0]) * 1.6 + DROPS[0] * 0.4
        else:
            seit = u - ENTHUELLEN
            hell, w = 1.0, ENTHUELLEN * 1.2 + 4 * seit + 10 * (1 - math.exp(-seit / 0.8))
        seit = u - DROPS[max(d, 0)]
        if d >= 0 and seit < BLITZ_S:
            s.fill(tuple(int(255 * (1 - seit / BLITZ_S) * (0.5 if d < 2 else 1)) for _ in range(3)))
        img = self.gedreht(w)
        if hell < 1:
            img = img.copy()
            img.fill((int(255 * hell),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        r = img.get_rect(center=(L.W // 2, L.H * 9 // 20))
        s.blit(img, r, special_flags=pygame.BLEND_RGB_ADD if self.blatt else 0)
        if u >= ENTHUELLEN:
            self.app.font.text(s, "DRAGONFIST", (L.W // 2, L.H * 9 // 20 + self.n * 2 // 5 + L.y(30)), "l", INK, "center")
        for x, y, _, _, c, a, _, g in self.konfetti:
            ca, sa = math.cos(a) * g, math.sin(a) * g * 0.5
            pygame.draw.polygon(s, c, ((x - ca, y - sa), (x + sa, y - ca * 0.4), (x + ca, y + sa), (x - sa, y + ca * 0.4)))
        if aus > 0:
            schwarz = pygame.Surface((L.W, L.H))
            schwarz.fill(BG)
            schwarz.set_alpha(int(255 * aus))
            s.blit(schwarz, (0, 0))

