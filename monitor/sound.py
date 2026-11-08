import time
from pathlib import Path

import numpy as np
import pygame

SR = 44100
ROOT = Path(__file__).resolve().parent.parent
WAVS = ROOT / "app" / "assets" / "sounds"
WAVES = ("sine", "square", "triangle", "saw", "noise")
NAMES = "C C# D D# E F F# G G# A A# B".split()

BASE = dict(wave="sine", notes=["A4"], ms=200, gap=0, attack=6, decay=12, slide=0, vibrato=0, harm=0.15, lofi=0,
            vol=0.2)
DEFAULTS = {
    "intro": dict(notes=["C3", "G3", "C4", "G4", "C5"], ms=1100, gap=35, decay=7, harm=0.19, vol=0.15),
    "move": dict(notes=["C6"], ms=45, decay=60, harm=0.14, vol=0.11),
    "ok": dict(notes=["E5", "B5"], ms=160, gap=40, decay=7, harm=0.19, vol=0.15),
    "back": dict(notes=["E5", "A4"], ms=160, gap=40, decay=7, harm=0.19, vol=0.13),
    "treffer": dict(notes=["G5", "B5", "E6"], ms=450, gap=55, decay=7, harm=0.19, vol=0.22),
    "verbunden": dict(notes=["C5", "E5", "G5"], ms=500, gap=90, decay=7, harm=0.19, vol=0.18),
    "getrennt": dict(notes=["G5", "D5", "G4"], ms=500, gap=110, decay=7, harm=0.19, vol=0.18),
    "bruch": dict(notes=["G4"], ms=260, decay=14, harm=0.15, vol=0.22),
    "frei": dict(notes=["D5"], ms=200, decay=18, harm=0.12, vol=0.15),
}


def midi(name):
    return NAMES.index(name[:-1]) + 12 * (int(name[-1]) + 1)


def _wave(kind, ph, rnd):
    if kind == "sine":
        return np.sin(ph)
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "triangle":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    step = np.floor(ph / np.pi).astype(np.int64)
    return rnd[step % len(rnd)]


def render(p):
    n = int(SR * p["ms"] / 1000)
    t = np.arange(n) / SR
    notes = [midi(x) for x in p["notes"] if x]
    out = np.zeros(n + int(SR * p["gap"] / 1000) * max(0, len(notes) - 1))
    rnd = np.random.default_rng(1).uniform(-1, 1, 4096)
    env = np.minimum(1, t / max(1e-4, p["attack"] / 1000)) * np.exp(-t * p["decay"])
    for k, m in enumerate(notes):
        f = 440 * 2 ** ((m - 69) / 12) * 2 ** ((p["slide"] * t / max(t[-1], 1e-4) +
                                                 p["vibrato"] * np.sin(2 * np.pi * 6 * t)) / 12)
        ph = 2 * np.pi * np.cumsum(f) / SR
        y = _wave(p["wave"], ph, rnd) + p["harm"] * _wave(p["wave"], 2 * ph, rnd)
        o = int(SR * p["gap"] / 1000) * k
        out[o:o + n] += y * env
    out = np.clip(out * p["vol"], -1, 1)
    if p["lofi"] >= 2:
        out = np.repeat(out[::4], 4)[:len(out)]
    if p["lofi"] >= 1:
        out = np.round(out * 127) / 127
    return out


def to_sound(y):
    ch = pygame.mixer.get_init()[2]
    a = (y * 32767).astype(np.int16)
    if ch > 1:
        a = np.repeat(a[:, None], ch, axis=1)
    return pygame.mixer.Sound(buffer=np.ascontiguousarray(a).tobytes())


class Sfx:
    def __init__(self):
        self.on = pygame.mixer.get_init() is not None
        self.snd, self.vol = {}, 1.0
        self.reload()

    def reload(self):
        if not self.on:
            return
        for k, p in DEFAULTS.items():
            p = BASE | p
            wav = WAVS / f"{k}.wav"
            self.snd[k] = pygame.mixer.Sound(str(wav)) if wav.exists() else to_sound(render(p))
        self.last = dict.fromkeys(self.snd, 0.0)
        self.volume(self.vol)

    def volume(self, v):
        self.vol = v
        for snd in self.snd.values():
            snd.set_volume(v)

    def play(self, kind):
        if not self.on or kind not in self.snd:
            return
        now = time.monotonic()
        if now - self.last[kind] > 0.04:
            self.last[kind] = now
            self.snd[kind].play()
