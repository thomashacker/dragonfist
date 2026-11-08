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

from monitor import State, reader
from punch import WRAP
from runlog import RunLog
from sound import Sfx
from inputs import Input
from scenes import W, H, BG, INK, DIM, GREEN, Intro

CFG_FILE = ROOT / "settings.json"
CFG = dict(audio=None, volume=80, ton=True, abstand=200)
MONO = "consolas,dejavusansmono,liberationmono,couriernew"


class Fonts:
    def __init__(self):
        self.f = {k: pygame.font.SysFont(MONO, n, bold=k in ("l", "xl")) for k, n in
                  (("xs", 13), ("s", 17), ("m", 22), ("l", 34), ("xl", 76))}
        self.cache = {}

    def text(self, s, t, pos, size="s", col=INK, anchor="topleft"):
        key = (t, size, col)
        img = self.cache.get(key)
        if img is None:
            img = self.cache[key] = self.f[size].render(t, True, col)
        r = img.get_rect(**{anchor: pos})
        s.blit(img, r)
        return r


class App:
    def __init__(self, a):
        pygame.mixer.pre_init(44100, -16, 1, 256)
        pygame.init()
        flags = pygame.SCALED | (pygame.FULLSCREEN if a.fullscreen else pygame.RESIZABLE)
        self.screen = pygame.display.set_mode((W, H), flags)
        pygame.display.set_caption("DRAGONFIST")
        self.cfg = dict(CFG)
        try:
            self.cfg |= json.loads(CFG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        if a.abstand:
            self.cfg["abstand"] = a.abstand
        self.font, self.force_mute = Fonts(), a.mute
        self.apply_audio()
        rl = None if a.no_log else RunLog(a.runs, *_names(), "app")
        self.st, self.stop, self.sim = State(rl, self.cfg["abstand"]), threading.Event(), a.sim
        self.input = Input(self.sim_edge if a.sim else None, self.sim_punch if a.sim else None)
        if a.sim:
            self.st.connect("SIM")
        else:
            threading.Thread(target=reader, args=(self.st, a.port, self.stop), daemon=True).start()
        self.stack, self.toast, self.sim_s, self.fade = [], None, 0.0, None
        self.black = pygame.Surface((W, H))
        self.black.fill(BG)
        self.push(Intro(self))

    def sim_edge(self, ch, v):
        self.st.feed(f"E {ch} {v} {int(time.perf_counter() * 1e6) % WRAP}")

    def sim_punch(self, hand):
        dt = int(self.cfg["abstand"] / 1000 / (random.uniform(10, 32) / 3.6) * 1e6)
        a, b = (0, 6) if hand == "L" else (5, 12)
        t = int(time.perf_counter() * 1e6)
        for ch, v, o in ((a, 0, 0), (b, 0, dt), (a, 1, dt + 30000), (b, 1, dt + 45000)):
            self.st.feed(f"E {ch} {v} {(t + o) % WRAP}")

    def save(self):
        CFG_FILE.write_text(json.dumps(self.cfg, indent=1), encoding="utf-8")

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
        self.sfx = Sfx()
        self.sfx.volume(self.cfg["volume"] / 100)

    @property
    def mute(self):
        return self.force_mute or not self.cfg["ton"]

    def push(self, sc):
        self.stack.append(sc)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()

    def replace(self, sc, fade=0.0):
        self.stack[-1] = sc
        self.fade = (time.monotonic(), fade) if fade else None

    def play(self, kind):
        self.mute or self.sfx.play(kind)

    def frame(self, actions, now):
        sc = self.stack[-1]
        for act in actions:
            sc.on(act)
            sc = self.stack[-1] if self.stack else sc
        if self.sim and now - self.sim_s >= 0.05:
            self.sim_s = now
            m = (1 << len(self.st.ch)) - 1
            for c in self.input.held_ch():
                m &= ~(1 << c)
            self.st.feed("S %x" % m)
        self.st.tick(now)
        with self.st.lock:
            snd, hits = list(dict.fromkeys(self.st.sfx)), list(self.st.hits)
            self.st.sfx.clear()
            self.st.hits.clear()
        for k in snd:
            k in sc.sounds and self.play(k)
        for r in hits:
            self.toast = r
            sc.punch(r)
        self.screen.fill(BG)
        sc.draw(self.screen, now)
        sc = self.stack[-1]
        if not (hasattr(sc, "ui") or getattr(sc, "bare", False)):
            self.overlay(now)
        if self.fade:
            k = (now - self.fade[0]) / self.fade[1]
            if k >= 1:
                self.fade = None
            else:
                self.black.set_alpha(int(255 * (1 - k)))
                self.screen.blit(self.black, (0, 0))

    def overlay(self, now):
        s, f = self.screen, self.font
        live = self.sim or self.st.live(now)
        f.text(s, "SIM" if self.sim else ("PICO" if live else "KEIN PICO"), (W - 16, 12), "xs",
               GREEN if live else DIM, "topright")
        r = self.toast
        if r and now - r["t"] < 2.5:
            hand = {"L": "LINKS", "R": "RECHTS"}.get(r["hand"], "")
            txt = f"{hand}  {r['v'] * 3.6:.1f} km/h" if r["ok"] else f"{hand}  {r['msg']}"
            f.text(s, txt, (W // 2, H - 64), "m", GREEN if r["ok"] else DIM, "center")
        hint = "↑↓ wählen · OK bestätigen · ZURÜCK"
        if self.sim:
            hint += " · A/D ändern · SIM: ← links · → rechts schlagen"
        f.text(s, hint, (W // 2, H - 16), "xs", DIM, "center")

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
                if shot and not script and now - t0 > 1.5:
                    pygame.image.save(self.screen, shot)
                    break
                clock.tick(60)
        finally:
            self.stop.set()
            if self.st.rl:
                with self.st.lock:
                    self.st.rl.close()


def _names():
    from monitor import NAME, GP
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
