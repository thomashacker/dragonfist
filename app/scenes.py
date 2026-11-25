import time
from pathlib import Path

import pygame

from netz import symbol


QUER, HOCH = (1024, 600), (600, 1024)


class L:
    """Logische Bildfläche; Abstände sind für 600 px Höhe entworfen und wachsen im Hochformat mit."""
    W, H, hoch = *QUER, False

    @classmethod
    def y(cls, v):
        return v * cls.H // 600


def ausrichten(hoch):
    (L.W, L.H), L.hoch = HOCH if hoch else QUER, hoch
BG, INK, DIM, LO, GREEN = (0, 0, 0), (235, 235, 235), (120, 120, 120), (50, 50, 50), (90, 230, 130)
ASSETS = Path(__file__).resolve().parent / "assets"


SPIEL = ("a", "b", "punkt", "fehl", "verbunden", "getrennt")
KEIN_WLAN = "KEIN WLAN"
AUSRICHTUNG = {"quer": "QUER", "hoch_l": "HOCH LINKS", "hoch_r": "HOCH RECHTS"}


class Scene:
    sounds = ("verbunden", "getrennt")
    music, leds = "title", "tanz"

    def __init__(self, app):
        self.app = app

    def on(self, a):
        if a == "back":
            self.app.pop()

    def punch(self, r):
        pass

    def tap(self, p):
        """Antippen: Ziel unter dem Finger wählen und auslösen; ohne Ziele wie OK."""
        ziele = getattr(self, "ziele", None)
        k = next((k for k, r in ziele if r.collidepoint(p)), None) if ziele else -1
        if k is not None:
            if k >= 0:
                self.sel = k
            self.on("ok")

    def draw(self, s, now):
        pass


class Tiles(Scene):
    title, size, cy, kopf = "", 280, 340, 104

    def __init__(self, app, items):
        super().__init__(app)
        self.items, self.sel = items, 0

    def on(self, a):
        if a in ("left", "right", "up", "down"):
            self.sel = (self.sel + (1 if a in ("right", "down") else -1)) % len(self.items)
            self.app.play("move")
        elif a == "ok":
            self.app.play("ok")
            self.items[self.sel][2]()
        elif a == "back":
            self.app.play("back")
            self.app.pop()

    def rects(self):
        n, size = len(self.items), self.size
        if L.hoch:
            top = L.y(self.kopf) + 40
            frei = L.H - 70 - top
            h = min(size * 2 // 3, frei * 6 // (7 * n))
            gap = h // 6
            y0 = top + (frei - n * h - (n - 1) * gap) // 2
            return [pygame.Rect(40, y0 + k * (h + gap), L.W - 80, h) for k in range(n)]
        size = min(size, int((L.W - 40) / (n + (n - 1) / 8)))
        gap = size // 8
        x0 = (L.W - n * size - (n - 1) * gap) // 2
        return [pygame.Rect(x0 + k * (size + gap), self.cy - size // 2, size, size) for k in range(n)]

    def draw_tiles(self, s, now):
        f, rects = self.app.font, self.rects()
        self.ziele = list(enumerate(r.copy() for r in rects))
        fits = lambda k, i: all(f.f[k].size(it[i])[0] <= rects[0].w - 24 for it in self.items)
        big, small = "l" if fits("l", 0) else "m", "s" if fits("s", 1) else "xs"
        for k, ((label, sub, _), r) in enumerate(zip(self.items, rects)):
            on = k == self.sel
            if on:
                r.inflate_ip(16, 16)
                pygame.draw.rect(s, INK, r)
            else:
                pygame.draw.rect(s, LO, r, 3)
            col = BG if on else INK
            f.text(s, label, (r.centerx, r.centery - (14 if sub else 0)), big, col, "center")
            sub and f.text(s, sub, (r.centerx, r.centery + 34), small, BG if on else DIM, "center")

    def draw(self, s, now):
        f = self.app.font
        f.text(s, self.title, (L.W // 2, L.y(64)), "l", INK, "center")
        pygame.draw.line(s, LO, (L.W // 2 - 220, L.y(104)), (L.W // 2 + 220, L.y(104)))
        self.draw_tiles(s, now)


class Title(Tiles):
    size, cy, kopf = 270, 360, 166

    def __init__(self, app):
        from training import Highscore
        super().__init__(app, [
            ("START", "", lambda: app.push(Modes(app))),
            ("EINSTELLUNGEN", "", lambda: app.push(Settings(app))),
            ("HIGHSCORE", "", lambda: app.push(Highscore(app))),
        ])

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "DRAGONFIST", (L.W // 2, L.y(100)), "xl", INK, "center")
        d = min(300, L.W // 2 - 40)
        pygame.draw.line(s, LO, (L.W // 2 - d, L.y(166)), (L.W // 2 + d, L.y(166)))
        self.draw_tiles(s, now)
        f.text(s, "v" + self.app.version, (L.W - 16, L.H - 44), "xs", DIM, "bottomright")
        n = self.app.netz
        symbol(s, (44, 50), n.online, GREEN, DIM)
        f.text(s, (n.ssid or "WLAN") if n.online else "OFFLINE", (80, 30), "xs", GREEN if n.online else DIM)

    def on(self, a):
        a != "back" and super().on(a)


class Modes(Tiles):
    title, size = "START", 210

    def __init__(self, app):
        from training import Training
        import modi
        super().__init__(app, [
            ("TRAINING", "Endlos", lambda: app.push(Training(app))),
            ("ZEIT", "Zeitlimit", lambda: app.push(modi.zeit(app))),
            ("SCHLÄGE", "Serie", lambda: app.push(modi.serie(app))),
            ("REAKTION", "Piep!", lambda: app.push(modi.reaktion(app))),
            ("PUNKTE", "Durchhalten", lambda: app.push(modi.Punkte(app))),
        ])


def _aufnahme(app):
    from aufnahme import Aufnahme
    return Aufnahme(app)


class Settings(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.sel, self.devs, self.netz_wahl, self.installiert = 0, app.audio_devices(), None, False
        c = app.cfg
        self.rows = [
            ("AUDIO-AUSGANG", lambda: c["audio"] or "Standard", self.audio, None),
            ("LAUTSTÄRKE", lambda: f"{c['volume']} %",
             lambda d: self.set("volume", min(100, max(0, c["volume"] + 10 * d))), None),
            ("TON", lambda: "AN" if c["ton"] else "AUS", lambda d: self.set("ton", not c["ton"]), None),
            ("MUSIK", lambda: "AN" if c["musik"] else "AUS", lambda d: self.set("musik", not c["musik"]), None),
            ("LICHT", lambda: f"{c['licht']} %",
             lambda d: self.set("licht", min(100, max(10, c["licht"] + 10 * d))), None),
            ("AUSRICHTUNG", lambda: AUSRICHTUNG.get(c["ausrichtung"], "QUER"), self.ausrichtung, None),
            ("WLAN", self.wlan_text, self.wlan, self.wlan_los),
            ("AUTO-UPDATE", lambda: "AN" if c["auto_update"] else "AUS",
             lambda d: self.set("auto_update", not c["auto_update"]), None),
            ("UPDATE", self.update_text, None, self.update_los),
            ("GERÄTE", lambda: app.geraete.text(app, time.monotonic()), None, None),
            ("TESTTON", lambda: "OK drücken", None, lambda: app.sfx.play("treffer")),
            ("ABSTAND A–B", lambda: f"{c['abstand']:g} mm", lambda d: self.abstand(d), None),
            ("KALIBRIERUNG", lambda: "OK drücken", None, lambda: app.push(Calibration(app))),
            ("SCHLAG-AUFNAHME", lambda: "OK drücken", None, lambda: app.push(_aufnahme(app))),
            ("APP BEENDEN", lambda: "", None, lambda: setattr(app, "running", False)),
        ]

    def set(self, k, v):
        self.app.cfg[k] = v
        if k == "volume":
            self.app.volume()
        self.app.save()

    def audio(self, d):
        cur = self.app.cfg["audio"]
        i = self.devs.index(cur) if cur in self.devs else 0
        self.app.cfg["audio"] = self.devs[(i + d) % len(self.devs)]
        self.app.apply_audio()
        self.app.save()
        self.app.play("ok")

    def ausrichtung(self, d):
        arten = list(AUSRICHTUNG)
        i = arten.index(self.app.cfg["ausrichtung"]) if self.app.cfg["ausrichtung"] in arten else 0
        self.set("ausrichtung", arten[(i + d) % len(arten)])
        self.app.ausrichtung()

    def wlan(self, d):
        n = self.app.netz
        wahl = n.profile + [KEIN_WLAN]
        cur = self.netz_wahl or n.ssid or KEIN_WLAN
        i = wahl.index(cur) if cur in wahl else -1 if d > 0 else 0
        self.netz_wahl, n.meldung = wahl[(i + d) % len(wahl)], None

    def _anders(self):
        return self.netz_wahl and self.netz_wahl != (self.app.netz.ssid or KEIN_WLAN)

    def wlan_los(self):
        if self._anders():
            n = self.app.netz
            n.trennen() if self.netz_wahl == KEIN_WLAN else n.verbinden(self.netz_wahl)
            self.app.play("ok")

    def wlan_text(self):
        n = self.app.netz
        if n.meldung:
            return n.meldung
        if self._anders():
            return f"{self.netz_wahl}  OK?"
        return n.ssid or KEIN_WLAN

    def update_text(self):
        neu = self.app.netz.update
        if self.installiert:
            return "wird installiert …"
        return f"v{neu} – OK installieren" if neu and neu != self.app.version else f"aktuell v{self.app.version}"

    def update_los(self):
        n = self.app.netz
        if n.update and n.update != self.app.version and not self.installiert:
            self.installiert = n.installieren()
            self.app.play("ok")

    def abstand(self, d):
        v = min(400, max(50, self.app.cfg["abstand"] + 5 * d))
        self.set("abstand", v)
        self.app.st.punch.dist = v / 1000

    def tap(self, p):
        k, box = next(((k, r) for k, r in self.ziele if r.collidepoint(p)), (None, None))
        if k is None:
            return
        if k != self.sel:
            self.sel = k
            self.app.play("move")
        elif self.rows[k][2]:
            self.on("right" if p[0] >= box.centerx else "left")
        else:
            self.on("ok")

    def on(self, a):
        label, val, change, act = self.rows[self.sel]
        if a in ("up", "down"):
            self.sel = (self.sel + (1 if a == "down" else -1)) % len(self.rows)
            self.app.play("move")
        elif a in ("left", "right") and change:
            change(1 if a == "right" else -1)
            self.app.play("move")
        elif a == "ok":
            act() if act else change and change(1)
        elif a == "back":
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "EINSTELLUNGEN", (L.W // 2, L.y(54)), "l", INK, "center")
        pygame.draw.line(s, LO, (L.W // 2 - 260, L.y(90)), (L.W // 2 + 260, L.y(90)))
        y0, bw = L.y(90) + 14, min(800, L.W - 32)
        step = min(L.y(58), (L.H - y0 - 46) // len(self.rows))
        self.ziele = []
        for k, (label, val, change, _) in enumerate(self.rows):
            box = pygame.Rect((L.W - bw) // 2, y0 + k * step, bw, step - 8)
            self.ziele.append((k, box))
            on = k == self.sel
            pygame.draw.rect(s, INK, box) if on else pygame.draw.rect(s, LO, box, 1)
            col = BG if on else INK
            f.text(s, label, (box.x + 18, box.centery), "m", col, "midleft")
            v = val()
            n = 24 if not L.hoch else 14
            v = v if len(v) <= n else v[:n - 1] + "…"
            if change and on:
                v = f"<  {v}  >"
            f.text(s, v, (box.right - 18, box.centery), "s", col if on else DIM, "midright")


class Placeholder(Scene):
    music, leds, sounds = "action", "spiel", SPIEL

    def __init__(self, app, name):
        super().__init__(app)
        self.name, self.n = name, {"L": 0, "R": 0}

    def punch(self, r):
        self.n[r["hand"]] += r["ok"]

    def on(self, a):
        if a == "back":
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, self.name, (L.W // 2, L.y(64)), "l", INK, "center")
        f.text(s, "KOMMT BALD", (L.W // 2, L.y(250)), "xl", INK, "center")
        f.text(s, f"Testschläge  L {self.n['L']}  ·  R {self.n['R']}", (L.W // 2, L.y(350)), "m", DIM, "center")


class Calibration(Scene):
    sounds, music, leds, bare = SPIEL, None, "spiel", True

    def __init__(self, app):
        super().__init__(app)
        from monitor import Ui
        self.ui = Ui(app.screen)

    def on(self, a):
        if a == "back":
            self.app.play("back")
            self.app.pop()
        elif a == "ok":
            self.app.st.marker()

    def draw(self, s, now):
        self.ui.s = s
        self.ui.draw(self.app.st, now)


class Intro(Scene):
    bare, music = True, None
    FADE_IN, HOLD, FADE_OUT, GAP = 0.9, 1.7, 0.6, 0.35

    def __init__(self, app):
        super().__init__(app)
        logo = pygame.image.load(str(ASSETS / "vietvodao.png")).convert_alpha()
        f = app.font.f["xl"]
        a, b = f.render("SCHMUHLSCHES", True, INK), f.render("WISSEN", True, INK)
        text = pygame.Surface((a.get_width(), a.get_height() * 2), pygame.SRCALPHA)
        text.blit(a, (0, 0))
        text.blit(b, ((a.get_width() - b.get_width()) // 2, a.get_height()))
        k = min(1, (L.W - 40) / text.get_width())
        text = pygame.transform.smoothscale(text, (int(text.get_width() * k), int(text.get_height() * k)))
        self.parts = [text, pygame.transform.smoothscale(logo, (380, 380))]
        self.white = []
        for p in self.parts:
            w = p.copy()
            w.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.white.append(w)
        self.t0, self.played = None, -1
        self.step = self.FADE_IN + self.HOLD + self.FADE_OUT

    def on(self, a):
        if a in ("ok", "back"):
            self.done()

    def done(self):
        self.app.replace(Title(self.app), 0.8)

    def draw(self, s, now):
        if self.t0 is None:
            self.t0 = now
        t = now - self.t0 - self.GAP
        i = int(t // (self.step + self.GAP)) if t > 0 else -1
        if i >= len(self.parts):
            return self.done()
        u = t - i * (self.step + self.GAP)
        if i < 0 or u > self.step:
            return
        if i != self.played:
            self.played = i
            self.app.play("intro")
        a = min(1, u / self.FADE_IN) if u < self.FADE_IN + self.HOLD else max(0, (self.step - u) / self.FADE_OUT)
        z = 0.9 + 0.12 * (u / self.step)
        img, wh = self.parts[i], self.white[i]
        size = (int(img.get_width() * z), int(img.get_height() * z))
        r = pygame.Rect((0, 0), size)
        r.center = (L.W // 2, L.H // 2)
        frame = pygame.transform.smoothscale(img, size)
        frame.set_alpha(int(255 * a * a))
        s.blit(frame, r)
        f = u - self.FADE_IN
        if 0 <= f < 0.35:
            fl = pygame.transform.smoothscale(wh, size)
            fl.set_alpha(int(170 * (1 - f / 0.35)))
            s.blit(fl, r)
