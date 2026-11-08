import time

import pygame

KEYS = {pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
        pygame.K_RETURN: "ok", pygame.K_KP_ENTER: "ok", pygame.K_SPACE: "ok",
        pygame.K_ESCAPE: "back", pygame.K_BACKSPACE: "back", pygame.K_a: "left", pygame.K_d: "right"}
SIM = {pygame.K_q: 0, pygame.K_w: 6, pygame.K_o: 5, pygame.K_p: 12}
PAD_BUTTONS = {0: "ok", 1: "back", 2: "ok", 3: "back"}
DEAD, DELAY, REPEAT = 0.6, 0.35, 0.12


class Input:
    def __init__(self, sim_feed=None, sim_punch=None):
        pygame.joystick.init()
        self.pads, self.sim, self.sim_punch, self.held = {}, sim_feed, sim_punch, set()
        self.dir, self.next = None, 0.0

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
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
            elif t == pygame.KEYUP and e.key in self.held:
                self.held.discard(e.key)
                self.sim(SIM[e.key], 1)
            elif t == pygame.JOYDEVICEADDED:
                j = pygame.joystick.Joystick(e.device_index)
                self.pads[j.get_instance_id()] = j
            elif t == pygame.JOYDEVICEREMOVED:
                self.pads.pop(e.instance_id, None)
            elif t == pygame.JOYBUTTONDOWN:
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
        if self.dir and time.monotonic() >= self.next:
            self.next = time.monotonic() + REPEAT
            out.append(self.dir)
        return out
