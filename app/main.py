import argparse
import json
import os
import random
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "monitor"))

import pygame

from monitor import font
from pico import State, reader
from punch import WRAP
from runlog import RunLog, schreiben
from sound import Sfx
from inputs import Input, drehung
from netz import Netz
from praesentation import Praesentation
from scenes import L, QUER, BG, INK, DIM, GREEN, Intro, ausrichten
from splash import hold_lock, status

VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
CFG_FILE = ROOT / "settings.json"
SCORES = ROOT / "highscores.json"
MUSIC = ROOT / "app" / "assets" / "music"
FARBE = dict(a=(255, 90, 0), b=(0, 255, 0), punkt=(0, 80, 255), fehl=(255, 0, 0))
HALTEN = dict(punkt=0.8, fehl=0.8)
CFG = dict(audio=None, volume=80, ton=True, musik=True, abstand=200, zeit_limit=30, serie_n=20, reak_runden=10,
           reak_kombo=1, ausrichtung="hoch_l", auto_update=False, licht=100)
DREHUNG = {"quer": 0, "hoch_l": 90, "hoch_r": -90}


class Fonts:
    def __init__(self):
        self.f = {k: font(n) for k, n in (("xs", 17), ("s", 22), ("m", 30), ("l", 46), ("xl", 100))}
        self.cache = {}

    def text(self, s, t, pos, size="s", col=INK, anchor="topleft"):
        key = (t, size, col, L.W)
        img = self.cache.get(key)
        if img is None:
            img, w = self.f[size].render(t, True, col), L.W - 24
            if img.get_width() > w:
                img = pygame.transform.smoothscale(img, (w, img.get_height() * w // img.get_width()))
            self.cache[key] = img
        r = img.get_rect(**{anchor: pos})
        s.blit(img, r)
        return r


class App:
    def __init__(self, a):
        pygame.mixer.pre_init(44100, -16, 1, 256)
        pygame.init()
        dummy = os.environ.get("SDL_VIDEODRIVER") == "dummy"
        self.flags = 0 if dummy else pygame.SCALED | (pygame.FULLSCREEN if a.fullscreen else pygame.RESIZABLE)
        self.voll, self.display = a.fullscreen and not dummy, None
        self.cfg = dict(CFG)
        try:
            self.cfg |= json.loads(CFG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        self.input = Input(self.sim_edge if a.sim else None, self.sim_punch if a.sim else None)
        self.ausrichtung()
        pygame.display.set_caption("DRAGONFIST")
        pygame.mouse.set_visible(False)
        if a.abstand:
            self.cfg["abstand"] = a.abstand
        self.font, self.force_mute, self.version, self.scores = Fonts(), a.mute, VERSION, SCORES
        self.apply_audio()
        self.netz = Netz()
        rl = None if a.no_log else RunLog(a.runs, *_names(), "app")
        self.st, self.stop, self.sim = State(rl, self.cfg["abstand"]), threading.Event(), a.sim
        if a.sim:
            self.st.connect("SIM")
        else:
            self.reader = threading.Thread(target=reader, args=(self.st, a.port, self.stop), daemon=True)
            self.reader.start()
        self.stack, self.toast, self.sim_s, self.fade, self.track = [], None, 0.0, None, None
        self.toasts, self.led, self.led_sent, self.led_t = {}, {"L": None, "R": None}, None, 0.0
        self.status, self.status_t, self.lock = None, 0.0, None
        self.push(Intro(self))

    def ausrichtung(self):
        """Hochformat: im Vollbild wird die Bildfläche aufs quer eingebaute Panel gedreht, im Fenster steht sie hoch."""
        art = self.cfg["ausrichtung"] if self.cfg["ausrichtung"] in DREHUNG else "quer"
        ausrichten(art != "quer")
        self.drehen = DREHUNG[art] if self.voll else 0
        if not (self.voll and self.display):
            self.display = pygame.display.set_mode(QUER if self.voll else (L.W, L.H), self.flags)
        self.screen = pygame.Surface((L.W, L.H)) if self.drehen else self.display
        self.input.wandeln = drehung(self.drehen, L.W, L.H)
        self.black = pygame.Surface((L.W, L.H))
        self.black.fill(BG)

    def sim_edge(self, ch, v):
        self.st.feed(f"E {ch} {v} {int(time.perf_counter() * 1e6) % WRAP}")

    def sim_punch(self, hand):
        dt, db = (int(self.cfg["abstand"] / 1000 / (random.uniform(lo, hi) / 3.6) * 1e6) for lo, hi in ((10, 32), (6, 18)))
        a, b = random.choice(((0, 6), (1, 7), (2, 8), (2, 9)) if hand == "L" else ((5, 12), (4, 11), (3, 10), (3, 9)))
        t = int(time.perf_counter() * 1e6)
        for ch, v, o in ((a, 0, 0), (b, 0, dt), (b, 1, dt + 30000), (a, 1, dt + 30000 + db)):
            self.st.feed(f"E {ch} {v} {(t + o) % WRAP}")

    def save(self):
        schreiben(CFG_FILE, self.cfg)

    def audio_devices(self):
        try:
            from pygame._sdl2 import audio
            return [None] + list(audio.get_audio_device_names(False))
        except (ImportError, pygame.error):
            return [None]

    def apply_audio(self):
        pygame.mixer.quit()
        try:
            pygame.mixer.init(44100, -16, 1, 256, devicename=self.cfg["audio"])
        except pygame.error:
            try:
                pygame.mixer.init(44100, -16, 1, 256)
            except pygame.error:
                pass
        self.sfx, self.track = Sfx(), None
        self.volume()

    def volume(self):
        v = self.cfg["volume"] / 100
        self.sfx.volume(v)
        try:
            pygame.mixer.music.set_volume(0.5 * v)
        except pygame.error:
            pass

    def music(self):
        want = self.stack[-1].music
        if want is False:
            self.track = False
            return
        want = None if self.mute or not self.cfg["musik"] else want
        if want == self.track:
            return
        self.track = want
        try:
            if want:
                pygame.mixer.music.load(str(MUSIC / f"{want}_theme.mp3"))
                pygame.mixer.music.play(-1, fade_ms=600)
            else:
                pygame.mixer.music.fadeout(400)
        except (pygame.error, FileNotFoundError):
            pass

    @property
    def mute(self):
        return self.force_mute or not self.cfg["ton"]

    def push(self, sc):
        self.stack.append(sc)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()

    def home(self, sc=None):
        del self.stack[1:]
        sc and self.push(sc)

    def replace(self, sc, fade=0.0):
        self.stack[-1] = sc
        self.fade = (time.monotonic(), fade) if fade else None

    def play(self, kind):
        self.mute or self.sfx.play(kind)

    def frame(self, actions, now):
        sc = self.stack[-1]
        for act in actions:
            if isinstance(act, tuple):
                sc.tap(act[1])
            elif act == "praesentation":
                if not isinstance(sc, Praesentation):
                    self.push(Praesentation(self))
            else:
                sc.on(act)
            sc = self.stack[-1] if self.stack else sc
        if self.sim and now - self.sim_s >= 0.05:
            self.sim_s = now
            m = (1 << len(self.st.ch)) - 1
            for c in self.input.held_ch():
                m &= ~(1 << c)
            self.st.feed("S %x" % m)
        self.music()
        self.st.tick(now)
        with self.st.lock:
            snd, hits, leds = list(dict.fromkeys(self.st.sfx)), list(self.st.hits), list(self.st.leds)
            self.st.sfx.clear()
            self.st.hits.clear()
            self.st.leds.clear()
        for k in snd:
            k in sc.sounds and self.play(k)
        for r in hits:
            self.toast = self.toasts[r["hand"]] = r
            sc.punch(r)
        self.lights(sc, leds, now)
        self.screen.fill(BG)
        sc.draw(self.screen, now)
        sc = self.stack[-1]
        if not (hasattr(sc, "ui") or getattr(sc, "bare", False)):
            self.overlay(now)
        if now - self.status_t >= 1:
            self.status, self.status_t = status(), now
        if self.status:
            r = self.font.text(self.screen, self.status, (L.W // 2, 14), "s", GREEN, "midtop").inflate(24, 12)
            pygame.draw.rect(self.screen, BG, r)
            pygame.draw.rect(self.screen, GREEN, r, 2)
            self.font.text(self.screen, self.status, r.center, "s", GREEN, "center")
        if self.fade:
            k = (now - self.fade[0]) / self.fade[1]
            if k >= 1:
                self.fade = None
            else:
                self.black.set_alpha(int(255 * (1 - k)))
                self.screen.blit(self.black, (0, 0))
        if self.drehen:
            self.display.blit(pygame.transform.rotate(self.screen, self.drehen), (0, 0))

    def lights(self, sc, leds, now):
        for k, hand in leds:
            self.led[hand] = (k, now + HALTEN[k] if k in HALTEN else None)
        if sc.leds == "show":
            cmd = sc.licht(now)
        elif sc.leds == "tanz":
            cmd = "T"
        elif sc.leds == "welle":
            periode, (r, g, b) = sc.welle()
            cmd = f"W {periode} {r:02x}{g:02x}{b:02x}"
        else:
            hex6 = []
            for hand in "LR":
                k = self.led[hand]
                if k and k[1] and now > k[1]:
                    k = self.led[hand] = None
                r, g, b = FARBE[k[0]] if k else (0, 0, 0)
                hex6.append(f"{r:02x}{g:02x}{b:02x}")
            cmd = "L " + " ".join(hex6)
        if cmd != self.led_sent or now - self.led_t > 1:
            self.led_sent, self.led_t = cmd, now
            self.st.send(f"D {self.cfg['licht']}")
            self.st.send(cmd)

    def overlay(self, now):
        s, f = self.screen, self.font
        live = self.sim or self.st.live(now)
        f.text(s, "SIM" if self.sim else ("PICO" if live else "KEIN PICO"), (L.W - 16, 12), "xs",
               GREEN if live else DIM, "topright")
        for hand, x in (("L", L.W * 3 // 10), ("R", L.W * 7 // 10)):
            r = self.toasts.get(hand)
            if r and now - r["t"] < 2.5:
                txt = f"{hand}  {r['v'] * 3.6:.1f} km/h" if r["v"] else f"{hand}  {r['msg']}"
                f.text(s, txt, (x, L.H - 64), "m", GREEN if r["ok"] else DIM, "center")
        hint = "A/D wählen · OK · ZURÜCK · SIM: ← links · → rechts" if self.sim else "←→ wählen · OK · ZURÜCK"
        f.text(s, hint, (L.W // 2, L.H - 16), "xs", DIM, "center")

    def run(self, shot=None, script=()):
        clock, self.running, t0 = pygame.time.Clock(), True, time.monotonic()
        script = list(script)
        try:
            while self.running:
                events = pygame.event.get()
                if any(e.type == pygame.QUIT for e in events):
                    break
                acts = self.input.events(events)
                if script and time.monotonic() - t0 > 0.3:
                    acts.append(script.pop(0))
                now = time.monotonic()
                self.frame(acts, now)
                pygame.display.flip()
                if not (shot or self.lock):
                    self.lock = hold_lock()
                if shot and not script and now - t0 > 1.5:
                    pygame.image.save(self.screen, shot)
                    break
                clock.tick(30 if self.stack[-1].leds == "tanz" else 60)
        finally:
            self.stop.set()
            if hasattr(self, "reader"):
                self.reader.join(1)
            if self.st.rl:
                with self.st.lock:
                    self.st.rl.close()


def _names():
    from pico import NAME, GP
    return NAME, GP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--port")
    ap.add_argument("--abstand", type=float)
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--mute", action="store_true")
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    ap.add_argument("--shot")
    ap.add_argument("--script", default="")
    a = ap.parse_args()
    if a.shot:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        a.mute = True
    App(a).run(a.shot, [x for x in a.script.split(",") if x])


if __name__ == "__main__":
    main()
