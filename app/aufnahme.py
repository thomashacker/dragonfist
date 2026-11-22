"""Schlag-Aufnahme: feste Zeit schlagen, danach die tatsächlich gemachten Schläge eingeben. Beides landet im Lauf-Log
(raw.log, Zeilen '# AUFNAHME …'), damit sich die Erkennung mit monitor/analyse.py gegen die Wahrheit prüfen lässt."""
import pygame

from scenes import W, H, BG, INK, DIM, LO, GREEN, SPIEL, Scene

DAUERN = (15, 30, 60)
ARTEN = ("FREI", "LANGSAM", "SCHNELL", "NUR LINKS", "NUR RECHTS", "ARM VORNE", "KREUZ")
PERSONEN = tuple("123456789")
ZEILEN = (("PERSON", PERSONEN), ("SCHLAGART", ARTEN), ("DAUER", DAUERN))
COUNTDOWN = 3


class Aufnahme(Scene):
    music, leds, sounds, bare = None, "spiel", SPIEL, True

    def __init__(self, app, wahl=(0, 0, 1)):
        super().__init__(app)
        self.wahl, self.zeile = list(wahl), 1
        self.phase, self.t0, self.punches, self.zahl, self.nr = "wahl", None, [], 0, 0

    @property
    def dauer(self):
        return DAUERN[self.wahl[2]]

    def wert(self, z):
        return str(ZEILEN[z][1][self.wahl[z]])

    def punch(self, r):
        if self.phase == "laeuft":
            self.punches.append(r)

    def on(self, a):
        app, ph = self.app, self.phase
        if a == "back" and ph in ("wahl", "fertig"):
            app.play("back")
            return app.pop()
        if ph == "wahl":
            if a in ("up", "down"):
                self.zeile = (self.zeile + (1 if a == "down" else -1)) % len(ZEILEN)
                app.play("move")
            elif a in ("left", "right"):
                z = self.zeile
                self.wahl[z] = (self.wahl[z] + (1 if a == "right" else -1)) % len(ZEILEN[z][1])
                app.play("move")
            elif a == "ok":
                app.play("ok")
                self.phase, self.t0 = "countdown", None
        elif ph == "zaehlen":
            d = {"up": 1, "down": -1, "right": 10, "left": -10}.get(a)
            if d:
                self.zahl = max(0, self.zahl + d)
                app.play("move")
            elif a == "ok":
                ok = [r for r in self.punches if r["ok"]]
                nl = sum(r["hand"] == "L" for r in ok)
                app.st.note(f"AUFNAHME ENDE erkannt={len(ok)} L={nl} R={len(ok) - nl} "
                            f"fehl={len(self.punches) - len(ok)} gezaehlt={self.zahl}")
                app.play("ok")
                self.phase = "fertig"
        elif ph == "fertig" and a == "ok":
            app.play("ok")
            self.__init__(app, self.wahl)
        elif a == "back":
            app.st.note("AUFNAHME ABBRUCH")
            app.play("back")
            self.__init__(app, self.wahl)

    def draw(self, s, now):
        f, ph = self.app.font, self.phase
        f.text(s, "SCHLAG-AUFNAHME", (W // 2, 46), "l", INK, "center")
        if ph == "wahl":
            f.text(s, "Schlagen und im Kopf mitzählen, danach die echte Zahl eingeben.", (W // 2, 120), "s", DIM,
                   "center")
            for z, (name, _) in enumerate(ZEILEN):
                y, on = 220 + z * 90, z == self.zeile
                f.text(s, name, (W // 2 - 60, y), "m", INK if on else DIM, "midright")
                wert = self.wert(z) + (" s" if name == "DAUER" else "")
                f.text(s, f"<  {wert}  >" if on else wert, (W // 2 + 180, y), "l", INK if on else DIM, "center")
            f.text(s, "▲▼ Zeile  ·  ◀▶ ändern  ·  OK Start  ·  ZURÜCK", (W // 2, H - 18), "xs", DIM, "center")
            return
        if self.t0 is None:
            self.t0 = now
        u = now - self.t0
        if ph == "countdown":
            n = COUNTDOWN - int(u)
            if n != self.nr:
                self.nr = n
                self.app.play("ok" if n <= 0 else "move")
            if n <= 0:
                self.phase, self.t0, self.punches = "laeuft", now, []
                self.app.st.note(f"AUFNAHME START dauer={self.dauer} person={self.wert(0)} "
                                 f"art={self.wert(1).replace(' ', '_')}")
                return
            f.text(s, str(n), (W // 2, 300), "xl", INK, "center")
            f.text(s, "gleich geht's los", (W // 2, 400), "m", DIM, "center")
        elif ph == "laeuft":
            rest = self.dauer - u
            if rest <= 0:
                self.app.play("intro")
                self.phase = "zaehlen"
                self.zahl = sum(r["ok"] for r in self.punches)
                return
            ok = [r for r in self.punches if r["ok"]]
            f.text(s, f"{rest:4.1f}", (W // 2, 230), "xl", GREEN, "center")
            pygame.draw.rect(s, LO, (W // 2 - 300, 300, 600, 14), 1)
            pygame.draw.rect(s, GREEN, (W // 2 - 300, 300, int(600 * u / self.dauer), 14))
            f.text(s, f"L {sum(r['hand'] == 'L' for r in ok)}   ·   R {sum(r['hand'] == 'R' for r in ok)}",
                   (W // 2, 400), "l", INK, "center")
            f.text(s, "ZURÜCK  abbrechen", (W // 2, H - 18), "xs", DIM, "center")
        elif ph == "zaehlen":
            f.text(s, "Wie viele Schläge hast du gemacht?", (W // 2, 160), "m", INK, "center")
            r = pygame.Rect(W // 2 - 150, 230, 300, 140)
            pygame.draw.rect(s, INK, r)
            f.text(s, str(self.zahl), r.center, "xl", BG, "center")
            f.text(s, "▲▼ ±1  ·  ◀▶ ±10  ·  OK bestätigen", (W // 2, H - 18), "xs", DIM, "center")
        else:
            ok = [r for r in self.punches if r["ok"]]
            q = len(ok) / self.zahl * 100 if self.zahl else 0
            f.text(s, f"{len(ok)}  von  {self.zahl}", (W // 2, 220), "xl", INK, "center")
            f.text(s, f"erkannt  ·  {q:.0f} %", (W // 2, 310), "m", GREEN if 95 <= q <= 105 else DIM, "center")
            nl = sum(r["hand"] == "L" for r in ok)
            f.text(s, f"L {nl}  ·  R {len(ok) - nl}  ·  Fehlschläge {len(self.punches) - len(ok)}", (W // 2, 370), "s",
                   DIM, "center")
            f.text(s, "gespeichert im Lauf-Log", (W // 2, 430), "s", DIM, "center")
            f.text(s, "OK  nochmal  ·  ZURÜCK", (W // 2, H - 18), "xs", DIM, "center")
