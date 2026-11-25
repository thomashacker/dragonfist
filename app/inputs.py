import time

import pygame

KEYS = {pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
        pygame.K_RETURN: "ok", pygame.K_KP_ENTER: "ok", pygame.K_SPACE: "ok",
        pygame.K_ESCAPE: "back", pygame.K_BACKSPACE: "back", pygame.K_a: "left", pygame.K_d: "right"}
SIM = {pygame.K_q: 0, pygame.K_w: 6, pygame.K_o: 5, pygame.K_p: 12}
PAD_BUTTONS = {0: "ok", 1: "back", 3: "back"}
GELB, HALTEN_S = 2, 5.0          # gelber Knopf: kurz "gelb", 5 s gehalten startet die Präsentation
DEAD, DELAY, REPEAT = 0.6, 0.35, 0.12
WISCH, LANG = 60, 0.8       # Touch: ab 60 px Wischen, ab 0,8 s Halten zurück


def drehung(d, w, h):
    """Bildschirmpunkt des gedrehten Panels → Punkt der logischen Bildfläche (w × h)."""
    if d == 90:
        return lambda p: (w - 1 - p[1], p[0])
    if d == -90:
        return lambda p: (p[1], h - 1 - p[0])
    return lambda p: p


class Input:
    def __init__(self, sim_feed=None, sim_punch=None):
        pygame.joystick.init()
        self.pads, self.sim, self.sim_punch, self.held = {}, sim_feed, sim_punch, set()
        self.dir, self.next, self.gelb, self.druck = None, 0.0, None, None
        self.wandeln = lambda p: p

    def held_ch(self):
        return [SIM[k] for k in self.held]

    def _stick(self, d, out):
        if d != self.dir:
            self.dir = d
            self.next = time.monotonic() + DELAY
            d and out.append(d)

    def events(self, events):
        out = []
        for e in events:
            t = e.type
            if t == pygame.KEYDOWN:
                if self.sim_punch and e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.sim_punch("L" if e.key == pygame.K_LEFT else "R")
                elif self.sim and e.key in SIM:
                    if e.key not in self.held:
                        self.held.add(e.key)
                        self.sim(SIM[e.key], 0)
                elif e.key in KEYS:
                    out.append(KEYS[e.key])
                elif e.key == pygame.K_g:
                    self.gelb = self.gelb or time.monotonic()
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
            elif t in (pygame.KEYUP, pygame.JOYBUTTONUP) and (e.key == pygame.K_g if t == pygame.KEYUP
                                                              else e.button == GELB):
                self.gelb and out.append("gelb")
                self.gelb = None
            elif t == pygame.KEYUP and e.key in self.held:
                self.held.discard(e.key)
                self.sim(SIM[e.key], 1)
            elif t == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.druck = self.wandeln(e.pos), time.monotonic()
            elif t == pygame.MOUSEBUTTONUP and e.button == 1 and self.druck:
                (x0, y0), _ = self.druck
                x, y = self.wandeln(e.pos)
                dx, dy, self.druck = x - x0, y - y0, None
                if max(abs(dx), abs(dy)) < WISCH:
                    out.append(("tap", (x0, y0)))
                else:
                    out.append(("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up"))
            elif t == pygame.JOYDEVICEADDED:
                j = pygame.joystick.Joystick(e.device_index)
                self.pads[j.get_instance_id()] = j
            elif t == pygame.JOYDEVICEREMOVED:
                self.pads.pop(e.instance_id, None)
            elif t == pygame.JOYBUTTONDOWN:
                if e.button == GELB:
                    self.gelb = time.monotonic()
                else:
                    out.append(PAD_BUTTONS.get(e.button, "ok"))
            elif t == pygame.JOYHATMOTION:
                x, y = e.value
                self._stick("left" if x < 0 else "right" if x > 0 else "up" if y > 0 else "down" if y < 0 else None,
                            out)
            elif t == pygame.JOYAXISMOTION and e.axis < 2:
                j = self.pads.get(e.instance_id)
                if j:
                    x, y = j.get_axis(0), j.get_axis(1)
                    d = None
                    if abs(x) > DEAD or abs(y) > DEAD:
                        d = ("right" if x > 0 else "left") if abs(x) > abs(y) else ("down" if y > 0 else "up")
                    self._stick(d, out)
        if self.gelb and time.monotonic() - self.gelb >= HALTEN_S:
            self.gelb = None
            out.append("praesentation")
        if self.druck and time.monotonic() - self.druck[1] >= LANG:
            self.druck = None
            out.append("back")
        if self.dir and time.monotonic() >= self.next:
            self.next = time.monotonic() + REPEAT
            out.append(self.dir)
        return out
