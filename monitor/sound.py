import math
import time
from array import array

import pygame

SR = 44100


def _tone(parts, ms, vol, decay):
    _, _, ch = pygame.mixer.get_init()
    n = SR * ms // 1000
    att = SR * 6 // 1000
    buf = array("h")
    for i in range(n):
        t = i / SR
        env = min(1.0, i / att) * math.exp(-t * decay)
        s = sum(a * math.sin(2 * math.pi * f * t) for f, a in parts)
        v = int(32767 * vol * env * s)
        buf.extend((v,) * ch)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _chord(notes, ms, vol, gap):
    _, _, ch = pygame.mixer.get_init()
    total = array("h", bytes(2 * ch * SR * (ms + gap * len(notes)) // 1000))
    for k, f in enumerate(notes):
        raw = array("h", _tone(((f, 0.8), (2 * f, 0.15)), ms, vol, 7).get_raw())
        off = ch * SR * gap * k // 1000
        for j, v in enumerate(raw):
            total[off + j] = max(-32767, min(32767, total[off + j] + v))
    return pygame.mixer.Sound(buffer=total.tobytes())


class Sfx:
    def __init__(self, vol=0.22):
        self.on = pygame.mixer.get_init() is not None
        if not self.on:
            return
        self.snd = {
            "bruch": _tone(((392, 0.8), (784, 0.12), (1176, 0.05)), 260, vol, 14),
            "frei": _tone(((587.3, 0.8), (1174.7, 0.1)), 200, vol * 0.7, 18),
            "verbunden": _chord((523.3, 659.3, 784), 500, vol * 0.8, 90),
            "getrennt": _chord((784, 587.3, 392), 500, vol * 0.8, 110),
            "treffer": _chord((784, 987.8, 1318.5), 450, vol, 55),
        }
        self.last = dict.fromkeys(self.snd, 0.0)

    def play(self, kind):
        if not self.on:
            return
        now = time.monotonic()
        if now - self.last[kind] > 0.04:
            self.last[kind] = now
            self.snd[kind].play()
