"""Spielmodi ZEIT, SCHLÄGE und REAKTION: einstellen, spielen, auswerten und speichern wie das Training."""
import math
import random
import time

import pygame

from scenes import W, H, BG, INK, DIM, LO, GREEN, SPIEL, Scene
from training import Stats, Wahl, auswerten, zaehler, _mittel

COUNTDOWN = 5
ROT = (255, 70, 60)


def _zeit(r):
    return r["tb_s"] if r.get("tb_s") is not None else r["t"]


class Setup(Scene):
    """Einstellungen eines Modus; die Wahl bleibt in settings.json."""
    bare = True

    def __init__(self, app, titel, zeilen, start):
        super().__init__(app)
        self.titel, self.zeilen, self.start, self.z = titel, zeilen, start, 0

    def wert(self, k):
        _, key, opts, _ = self.zeilen[k]
        v = self.app.cfg.get(key)
        return v if v in opts else opts[0]

    def on(self, a):
        app = self.app
        if a in ("up", "down"):
            self.z = (self.z + (1 if a == "down" else -1)) % len(self.zeilen)
            app.play("move")
        elif a in ("left", "right"):
            _, key, opts, _ = self.zeilen[self.z]
            app.cfg[key] = opts[(opts.index(self.wert(self.z)) + (1 if a == "right" else -1)) % len(opts)]
            app.save()
            app.play("move")
        elif a == "ok":
            app.play("ok")
            app.push(self.start(app, *[self.wert(k) for k in range(len(self.zeilen))]))
        elif a == "back":
            app.play("back")
            app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, self.titel, (W // 2, 60), "l", INK, "center")
        y0 = 300 - (len(self.zeilen) - 1) * 80
        for k, (name, _, _, einheit) in enumerate(self.zeilen):
            y, on = y0 + k * 160, k == self.z
            f.text(s, name, (W // 2, y - 66), "s", INK if on else DIM, "center")
            w = f"{self.wert(k)}{einheit}"
            f.text(s, f"<  {w}  >" if on else w, (W // 2, y + 10), "xl" if on else "l", INK if on else DIM, "center")
        hilfe = "▲▼ Zeile  ·  " if len(self.zeilen) > 1 else ""
        f.text(s, hilfe + "◀▶ ändern  ·  OK Start  ·  ZURÜCK", (W // 2, H - 18), "xs", DIM, "center")


class Spiel(Scene):
    music, leds, sounds, bare = "action", "spiel", SPIEL, True

    def __init__(self, app):
        super().__init__(app)
        self.punches, self.nr = [], None

    def on(self, a):
        if a == "back":
            self.app.play("back")
            self.app.pop()

    def ton(self, n, laut="tick"):
        if n != self.nr:
            self.nr = n
            self.app.play(laut)


class Zeit(Spiel):
    """5 s Countdown, dann läuft das Zeitlimit; die letzten 5 s werden mitgezählt."""

    def __init__(self, app, limit):
        super().__init__(app)
        self.limit, self.phase, self.t0, self.start, self.ende = limit, "countdown", None, None, None

    def punch(self, r):
        if self.start is not None and self.start <= _zeit(r) <= (self.ende or 1e18):
            self.punches.append(r | {"t": _zeit(r) - self.start})

    def draw(self, s, now):
        f = self.app.font
        if self.t0 is None:
            self.t0 = now
        f.text(s, f"ZEIT  ·  {self.limit} s", (W // 2, 46), "l", INK, "center")
        if self.phase == "countdown":
            n = COUNTDOWN - int(now - self.t0)
            if n <= 0:
                self.phase, self.start = "laeuft", now
                self.app.play("los")
                return
            self.ton(n)
            f.text(s, str(n), (W // 2, 280), "xl", INK, "center")
            f.text(s, "bereit machen", (W // 2, 370), "m", DIM, "center")
            return
        rest = self.limit - (now - self.start)
        if self.phase == "laeuft" and rest <= 0:
            self.phase, self.ende = "nachlauf", self.start + self.limit
            self.app.play("ende")
        if self.phase == "nachlauf":
            if now - self.ende > 0.6:
                st = auswerten(self.punches, self.limit) | dict(disz="ZEIT", ziel=self.limit)
                self.app.replace(Stats(self.app, st), 0.4)
            f.text(s, "ZEIT!", (W // 2, 170), "xl", GREEN, "center")
        else:
            letzte = rest <= COUNTDOWN
            letzte and self.ton(math.ceil(rest))
            f.text(s, str(math.ceil(rest)) if letzte else f"{rest:.1f}", (W // 2, 170), "xl", ROT if letzte else GREEN,
                   "center")
            pygame.draw.rect(s, LO, (W // 2 - 300, 230, 600, 12), 1)
            pygame.draw.rect(s, GREEN, (W // 2 - 300, 230, int(600 * (1 - rest / self.limit)), 12))
        zaehler(s, f, [r for r in self.punches if r["ok"]], 350)
        f.text(s, "ZURÜCK  abbrechen", (W // 2, H - 18), "xs", DIM, "center")


class Serie(Spiel):
    """Die Uhr läuft ab dem ersten Schlag und stoppt, sobald die Schlagzahl erreicht ist."""

    def __init__(self, app, ziel):
        super().__init__(app)
        self.ziel, self.start, self.dauer, self.t_ende = ziel, None, None, None

    def punch(self, r):
        if self.dauer is not None or (self.start is None and not r["ok"]):
            return
        if self.start is None:
            self.start = r["ta_s"] if r.get("ta_s") is not None else _zeit(r)
            self.app.play("los")
        self.punches.append(r | {"t": _zeit(r) - self.start})
        if sum(x["ok"] for x in self.punches) >= self.ziel:
            self.dauer = max(_zeit(r) - self.start, 1e-3)
            self.app.play("ende")

    def draw(self, s, now):
        f = self.app.font
        f.text(s, f"SCHLÄGE  ·  {self.ziel}", (W // 2, 46), "l", INK, "center")
        n = sum(r["ok"] for r in self.punches)
        if self.dauer is not None:
            self.t_ende = self.t_ende or now
            if now - self.t_ende > 1.5:
                st = auswerten(self.punches, self.dauer) | dict(disz="SCHLÄGE", ziel=self.ziel)
                return self.app.replace(Stats(self.app, st), 0.4)
            uhr, col = self.dauer, GREEN
        elif self.start is None:
            uhr, col = 0.0, DIM
            f.text(s, "Los geht's mit dem ersten Schlag", (W // 2, 250), "s", DIM, "center")
        else:
            uhr, col = now - self.start, INK
        f.text(s, f"{uhr:.2f}", (W // 2, 160), "xl", col, "center")
        pygame.draw.rect(s, LO, (W // 2 - 300, 220, 600, 12), 1)
        pygame.draw.rect(s, GREEN, (W // 2 - 300, 220, int(600 * min(1, n / self.ziel)), 12))
        zaehler(s, f, [r for r in self.punches if r["ok"]], 350, f"{n} / {self.ziel}")
        f.text(s, "ZURÜCK  abbrechen", (W // 2, H - 18), "xs", DIM, "center")


class Reaktion(Spiel):
    """Nach einer zufälligen Pause piept es; gemessen wird bis die Kombo durch Ebene B ist."""
    music = None
    PAUSE, ZEIGEN, MAX_S = (1.5, 3.5), 1.3, 3.0

    def __init__(self, app, runden, kombo, rnd=None):
        super().__init__(app)
        self.runden, self.kombo, self.rnd = runden, kombo, rnd or random.Random()
        self.zeiten, self.fehlstart, self.treffer = [], 0, []
        self.phase, self.t_phase, self.t_piep, self.t_runde, self.msg = "neu", None, None, 0.0, ""

    def punch(self, r):
        ts = r["ta_s"] if r.get("ta_s") is not None else _zeit(r)
        if self.phase not in ("warten", "jetzt") or ts < self.t_runde:
            return
        self.punches.append(r)
        if self.phase == "warten" or ts < self.t_piep:
            self.fehlstart += 1
            self.app.play("fehl")
            self.phase, self.t_phase, self.msg = "anzeige", time.monotonic(), "FEHLSTART"
            return
        if r["ok"]:
            self.treffer.append(r)
            if len(self.treffer) >= self.kombo:
                t = (_zeit(self.treffer[0]) - self.t_piep, _zeit(r) - self.t_piep)
                self.zeiten.append(t)
                self.phase, self.t_phase, self.msg = "anzeige", time.monotonic(), f"{t[1] * 1000:.0f} ms"

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "REAKTION", (W // 2, 46), "l", INK, "center")
        if self.phase == "neu":
            if len(self.zeiten) >= self.runden:
                return self.fertig(now)
            self.phase, self.t_phase, self.t_runde, self.treffer = "warten", now, now, []
            self.t_piep = now + self.rnd.uniform(*self.PAUSE)
        elif self.phase == "warten" and now >= self.t_piep:
            self.phase, self.t_phase = "jetzt", now
            self.app.play("piep")
        elif self.phase == "jetzt" and now - self.t_piep > self.MAX_S:
            self.zeiten.append((None, None))
            self.phase, self.t_phase, self.msg = "anzeige", now, "ZU LANGSAM"
        elif self.phase == "anzeige" and now - self.t_phase > self.ZEIGEN:
            self.phase = "neu"
        k = min(len(self.zeiten) + 1, self.runden)
        f.text(s, f"RUNDE {k} / {self.runden}  ·  KOMBO {self.kombo}", (W // 2, 110), "s", DIM, "center")
        if self.phase == "jetzt":
            pygame.draw.rect(s, GREEN, (W // 2 - 260, 170, 520, 220))
            f.text(s, "JETZT!", (W // 2, 260), "xl", BG, "center")
            if self.kombo > 1:
                f.text(s, f"{len(self.treffer)} / {self.kombo}", (W // 2, 350), "m", BG, "center")
        elif self.phase == "anzeige":
            gut = self.msg.endswith("ms")
            f.text(s, self.msg, (W // 2, 280), "xl", GREEN if gut else ROT, "center")
        else:
            f.text(s, "warten …", (W // 2, 280), "l", DIM, "center")
        gut = [t for _, t in self.zeiten if t is not None]
        if gut:
            f.text(s, f"Ø {_mittel(gut) * 1000:.0f} ms  ·  beste {min(gut) * 1000:.0f} ms  ·  Fehlstarts {self.fehlstart}",
                   (W // 2, 470), "s", DIM, "center")
        f.text(s, "ZURÜCK  abbrechen", (W // 2, H - 18), "xs", DIM, "center")

    def fertig(self, now):
        gut = [t for _, t in self.zeiten if t is not None]
        if not gut:
            return self.app.pop()
        ok = [r for r in self.punches if r["ok"]]
        t0 = min((_zeit(r) for r in self.punches), default=now)
        st = auswerten([r | {"t": _zeit(r) - t0} for r in self.punches], max(now - t0, 1)) | dict(
            disz="REAKTION", ziel=self.runden, kombo=self.kombo, zeiten=self.zeiten, r_avg=round(_mittel(gut), 4),
            r_best=round(min(gut), 4), fehlstart=self.fehlstart, n_ok=len(ok))
        self.app.replace(ReaktionStats(self.app, st), 0.4)


class ReaktionStats(Scene):
    bare = True

    def __init__(self, app, st):
        super().__init__(app)
        self.st, self.t0 = st, None

    def on(self, a):
        if a in ("ok", "back"):
            self.app.play("ok")
            self.app.push(Wahl(self.app, self.st))

    def draw(self, s, now):
        if self.t0 is None:
            self.t0 = now
        k = min(1.0, (now - self.t0) / 1.5)
        f, st = self.app.font, self.st
        f.text(s, "REAKTIONSZEITEN", (W // 2, 46), "l", INK, "center")
        r = pygame.Rect(80, 130, 600, 320)
        pygame.draw.rect(s, LO, r, 1)
        werte = [t for _, t in st["zeiten"]]
        ymax = max([t for t in werte if t] + [0.5]) * 1.15
        bw = r.w / max(1, len(werte))
        for i, t in enumerate(werte[:max(1, int(len(werte) * k + 0.999))]):
            if t is None:
                f.text(s, "×", (r.x + (i + 0.5) * bw, r.bottom - 20), "s", ROT, "center")
                continue
            h = int(r.h * t / ymax)
            col = GREEN if t == st["r_best"] else INK
            pygame.draw.rect(s, col, (r.x + i * bw + bw * 0.15, r.bottom - h, bw * 0.7, h))
        f.text(s, f"{ymax * 1000:.0f} ms", (r.x - 10, r.y), "xs", DIM, "topright")
        f.text(s, "0", (r.x - 10, r.bottom), "xs", DIM, "bottomright")
        for y, name, wert, col in ((140, "Ø", st["r_avg"], INK), (250, "BESTE", st["r_best"], GREEN)):
            f.text(s, name, (730, y), "s", DIM)
            f.text(s, f"{wert * 1000 * k:.0f}", (730, y + 26), "l", col)
            f.text(s, "ms", (730 + f.f["l"].size(f"{wert * 1000:.0f}")[0] + 10, y + 46), "xs", DIM)
        f.text(s, "FEHLSTARTS", (730, 360), "s", DIM)
        f.text(s, str(st["fehlstart"]), (730, 386), "l", ROT if st["fehlstart"] else INK)
        f.text(s, f"KOMBO {st['kombo']}  ·  {st['ziel']} RUNDEN", (r.centerx, r.bottom + 30), "s", DIM, "center")
        f.text(s, "OK  speichern oder verwerfen", (W // 2, H - 18), "xs", DIM, "center")


def zeit(app):
    return Setup(app, "ZEIT", [("ZEITLIMIT", "zeit_limit", (10, 20, 30, 60), " s")], Zeit)


def serie(app):
    return Setup(app, "SCHLÄGE", [("SCHLAGANZAHL", "serie_n", (10, 20, 50, 100), "")], Serie)


def reaktion(app):
    return Setup(app, "REAKTION", [("RUNDEN", "reak_runden", (5, 10, 20), ""),
                                   ("SCHLÄGE PRO KOMBO", "reak_kombo", (1, 2, 3, 4), "")], Reaktion)
