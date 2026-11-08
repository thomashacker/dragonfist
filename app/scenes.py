from pathlib import Path

import pygame


W, H = 1024, 600
BG, INK, DIM, LO, GREEN = (0, 0, 0), (235, 235, 235), (120, 120, 120), (50, 50, 50), (90, 230, 130)
ASSETS = Path(__file__).resolve().parent / "assets"


class Scene:
    sounds = ("treffer", "verbunden", "getrennt")

    def __init__(self, app):
        self.app = app

    def on(self, a):
        if a == "back":
            self.app.pop()

    def punch(self, r):
        pass

    def draw(self, s, now):
        pass


class Menu(Scene):
    title = ""

    def __init__(self, app, items):
        super().__init__(app)
        self.items, self.sel = items, 0

    def on(self, a):
        if a in ("up", "down"):
            self.sel = (self.sel + (1 if a == "down" else -1)) % len(self.items)
            self.app.play("move")
        elif a == "ok":
            self.app.play("ok")
            self.items[self.sel][1]()
        elif a == "back":
            self.app.play("back")
            self.app.pop()

    def draw_items(self, s, now, y0, gap=56):
        f = self.app.font
        for k, (label, _) in enumerate(self.items):
            y = y0 + k * gap
            box = pygame.Rect(0, 0, 340, 44)
            box.center = (W // 2, y)
            if k == self.sel:
                pygame.draw.rect(s, INK, box)
            else:
                pygame.draw.rect(s, LO, box, 1)
            f.text(s, label, box.center, "m", BG if k == self.sel else INK, "center")

    def draw(self, s, now):
        f = self.app.font
        f.text(s, self.title, (W // 2, 70), "l", INK, "center")
        pygame.draw.line(s, LO, (W // 2 - 170, 104), (W // 2 + 170, 104))
        self.draw_items(s, now, 180)


class Title(Menu):
    def __init__(self, app):
        super().__init__(app, [
            ("STORY", lambda: app.push(Placeholder(app, "STORY"))),
            ("ARENA", lambda: app.push(Arena(app))),
            ("EINSTELLUNGEN", lambda: app.push(Settings(app))),
            ("KALIBRIERUNG", lambda: app.push(Calibration(app))),
        ])

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "DRAGONFIST", (W // 2, 130), "xl", INK, "center")
        pygame.draw.line(s, LO, (W // 2 - 260, 190), (W // 2 + 260, 190))
        self.draw_items(s, now, 280)

    def on(self, a):
        a != "back" and super().on(a)


class Arena(Menu):
    title = "ARENA"

    def __init__(self, app):
        super().__init__(app, [(n, lambda n=n: app.push(Placeholder(app, n)))
                               for n in ("ZEITLIMIT", "SERIE", "REAKTION", "ENDLOS")])


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
            ("TESTTON", lambda: "OK drücken", None, lambda: app.sfx.play("treffer")),
            ("ABSTAND A–B", lambda: f"{c['abstand']:g} mm", lambda d: self.abstand(d), None),
            ("APP BEENDEN", lambda: "", None, lambda: setattr(app, "running", False)),
        ]

    def set(self, k, v):
        self.app.cfg[k] = v
        if k == "volume":
            self.app.sfx.volume(v / 100)
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
        f.text(s, "EINSTELLUNGEN", (W // 2, 70), "l", INK, "center")
        pygame.draw.line(s, LO, (W // 2 - 220, 104), (W // 2 + 220, 104))
        for k, (label, val, change, _) in enumerate(self.rows):
            box = pygame.Rect(W // 2 - 340, 150 + k * 56, 680, 44)
            on = k == self.sel
            pygame.draw.rect(s, INK, box) if on else pygame.draw.rect(s, LO, box, 1)
            col = BG if on else INK
            f.text(s, label, (box.x + 18, box.centery), "m", col, "midleft")
            v = val()
            v = v if len(v) <= 30 else v[:29] + "…"
            if change and on:
                v = f"<  {v}  >"
            f.text(s, v, (box.right - 18, box.centery), "s", col if on else DIM, "midright")


class Placeholder(Scene):
    def __init__(self, app, name):
        super().__init__(app)
        self.name, self.n = name, 0

    def punch(self, r):
        self.n += r["ok"]

    def on(self, a):
        if a == "back":
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, self.name, (W // 2, 70), "l", INK, "center")
        f.text(s, "KOMMT BALD", (W // 2, 250), "xl", INK, "center")
        f.text(s, f"Testschläge: {self.n}", (W // 2, 330), "m", DIM, "center")


class Calibration(Scene):
    sounds = ("bruch", "frei", "treffer", "verbunden", "getrennt")

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
    bare = True
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
