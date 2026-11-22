from pathlib import Path

import pygame

from netz import symbol


W, H = 1024, 600
BG, INK, DIM, LO, GREEN = (0, 0, 0), (235, 235, 235), (120, 120, 120), (50, 50, 50), (90, 230, 130)
ASSETS = Path(__file__).resolve().parent / "assets"


SPIEL = ("a", "b", "punkt", "fehl", "verbunden", "getrennt")


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

    def draw(self, s, now):
        pass


class Tiles(Scene):
    title, size, cy = "", 280, 340

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

    def draw_tiles(self, s, now):
        f, n, size = self.app.font, len(self.items), self.size
        gap = size // 8
        x0 = (W - n * size - (n - 1) * gap) // 2
        fits = lambda k, i: all(f.f[k].size(it[i])[0] <= size - 24 for it in self.items)
        big, small = "l" if fits("l", 0) else "m", "s" if fits("s", 1) else "xs"
        for k, (label, sub, _) in enumerate(self.items):
            r = pygame.Rect(x0 + k * (size + gap), self.cy - size // 2, size, size)
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
        f.text(s, self.title, (W // 2, 64), "l", INK, "center")
        pygame.draw.line(s, LO, (W // 2 - 220, 104), (W // 2 + 220, 104))
        self.draw_tiles(s, now)


class Title(Tiles):
    size, cy = 270, 360

    def __init__(self, app):
        from training import Highscore
        super().__init__(app, [
            ("START", "", lambda: app.push(Modes(app))),
            ("EINSTELLUNGEN", "", lambda: app.push(Settings(app))),
            ("HIGHSCORE", "", lambda: app.push(Highscore(app))),
        ])

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "DRAGONFIST", (W // 2, 100), "xl", INK, "center")
        pygame.draw.line(s, LO, (W // 2 - 300, 166), (W // 2 + 300, 166))
        self.draw_tiles(s, now)
        f.text(s, "v" + self.app.version, (W - 16, H - 44), "xs", DIM, "bottomright")
        n = self.app.netz
        symbol(s, (44, 50), n.online, GREEN, DIM)
        f.text(s, (n.ssid or "WLAN") if n.online else "OFFLINE", (80, 30), "xs", GREEN if n.online else DIM)

    def on(self, a):
        a != "back" and super().on(a)


class Modes(Tiles):
    title = "START"

    def __init__(self, app):
        from training import Training
        super().__init__(app, [
            ("TRAINING", "Endlos", lambda: app.push(Training(app))),
        ])


class Arena(Tiles):
    title, size = "ARENA", 210

    def __init__(self, app):
        super().__init__(app, [(n, "", lambda n=n: app.push(Placeholder(app, n)))
                               for n in ("ZEITLIMIT", "SERIE", "REAKTION", "ENDLOS")])


def _aufnahme(app):
    from aufnahme import Aufnahme
    return Aufnahme(app)


class Settings(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.sel, self.devs = 0, app.audio_devices()
        c = app.cfg
        self.rows = [
            ("AUDIO-AUSGANG", lambda: c["audio"] or "Standard", self.audio, None),
            ("LAUTSTÄRKE", lambda: f"{c['volume']} %",
             lambda d: self.set("volume", min(100, max(0, c["volume"] + 10 * d))), None),
            ("TON", lambda: "AN" if c["ton"] else "AUS", lambda d: self.set("ton", not c["ton"]), None),
            ("MUSIK", lambda: "AN" if c["musik"] else "AUS", lambda d: self.set("musik", not c["musik"]), None),
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

    def abstand(self, d):
        v = min(400, max(50, self.app.cfg["abstand"] + 5 * d))
        self.set("abstand", v)
        self.app.st.punch.dist = v / 1000

    def on(self, a):
        label, val, change, act = self.rows[self.sel]
        if a in ("up", "down"):
            self.sel = (self.sel + (1 if a == "down" else -1)) % len(self.rows)
            self.app.play("move")
        elif a in ("left", "right") and change:
            change(1 if a == "right" else -1)
            self.app.play("move")
        elif a == "ok":
            act() if act else change(1)
        elif a == "back":
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "EINSTELLUNGEN", (W // 2, 54), "l", INK, "center")
        pygame.draw.line(s, LO, (W // 2 - 260, 90), (W // 2 + 260, 90))
        step = min(58, (H - 150) // len(self.rows))
        for k, (label, val, change, _) in enumerate(self.rows):
            box = pygame.Rect(W // 2 - 400, 104 + k * step, 800, step - 8)
            on = k == self.sel
            pygame.draw.rect(s, INK, box) if on else pygame.draw.rect(s, LO, box, 1)
            col = BG if on else INK
            f.text(s, label, (box.x + 18, box.centery), "m", col, "midleft")
            v = val()
            v = v if len(v) <= 24 else v[:23] + "…"
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
        f.text(s, self.name, (W // 2, 64), "l", INK, "center")
        f.text(s, "KOMMT BALD", (W // 2, 250), "xl", INK, "center")
        f.text(s, f"Testschläge  L {self.n['L']}  ·  R {self.n['R']}", (W // 2, 350), "m", DIM, "center")


class Calibration(Scene):
    sounds, music, leds = SPIEL, None, "spiel"

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
        r.center = (W // 2, H // 2)
        frame = pygame.transform.smoothscale(img, size)
        frame.set_alpha(int(255 * a * a))
        s.blit(frame, r)
        f = u - self.FADE_IN
        if 0 <= f < 0.35:
            fl = pygame.transform.smoothscale(wh, size)
            fl.set_alpha(int(170 * (1 - f / 0.35)))
            s.blit(fl, r)
