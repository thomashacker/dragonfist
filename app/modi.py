"""Spielmodi ZEIT, SCHLÄGE und REAKTION: einstellen, spielen, auswerten und speichern wie das Training."""
import math
import random
import time

import pygame

from scenes import L, BG, INK, DIM, LO, GREEN, SPIEL, Scene
from training import Stats, Wahl, auswerten, graf_rect, kennzahlen, mmss, zaehler, _mittel

COUNTDOWN = 5
ROT = (255, 70, 60)


def _zeit(r):
    return r["tb_s"] if r.get("tb_s") is not None else r["t"]


UHR = (10, 10, 6, 10)


def _ziffern(v, basen):
    d = []
    for b in reversed(basen):
        v, r = divmod(v, b)
        d.append(r)
    return d[::-1]


def _zahl(d, basen):
    v = 0
    for x, b in zip(d, basen):
        v = v * b + x
    return v


class Setup(Scene):
    """Einstellungen eines Modus Stelle für Stelle; die Werte bleiben in settings.json."""
    bare = True

    def __init__(self, app, titel, zeilen, start):
        super().__init__(app)
        self.titel, self.zeilen, self.start = titel, zeilen, start
        self.stellen = [(k, i) for k, z in enumerate(zeilen) for i in range(len(z[2]))]
        self.c = len(zeilen[0][2]) - 1

    def wert(self, k):
        _, key, basen, _ = self.zeilen[k]
        hi = _zahl([b - 1 for b in basen], basen)
        return min(max(int(self.app.cfg.get(key) or 0), 0), hi)

    def on(self, a):
        app = self.app
        if a in ("left", "right"):
            self.c = (self.c + (1 if a == "right" else -1)) % len(self.stellen)
            app.play("move")
        elif a in ("up", "down"):
            k, i = self.stellen[self.c]
            _, key, basen, _ = self.zeilen[k]
            d = _ziffern(self.wert(k), basen)
            d[i] = (d[i] + (1 if a == "up" else -1)) % basen[i]
            app.cfg[key] = _zahl(d, basen)
            app.save()
            app.play("move")
        elif a == "ok":
            app.play("ok")
            app.push(self.start(app, *[max(1, self.wert(k)) for k in range(len(self.zeilen))]))
        elif a == "back":
            app.play("back")
            app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, self.titel, (L.W // 2, L.y(60)), "l", INK, "center")
        y0 = 300 - (len(self.zeilen) - 1) * 80
        ck, ci = self.stellen[self.c]
        for k, (name, _, basen, einheit) in enumerate(self.zeilen):
            y, on, gr = L.y(y0 + k * 160), k == ck, "xl" if k == ck else "l"
            f.text(s, name, (L.W // 2, y - 66), "s", INK if on else DIM, "center")
            zeichen = [(str(z), i) for i, z in enumerate(_ziffern(self.wert(k), basen))]
            if basen is UHR:
                zeichen.insert(2, (":", None))
            breiten = [f.f[gr].size(z)[0] for z, _ in zeichen]
            x = L.W // 2 - sum(breiten) // 2
            for (z, i), b in zip(zeichen, breiten):
                cur = on and i == ci
                r = f.text(s, z, (x, y + 10), gr, GREEN if cur else INK if on else DIM, "midleft")
                if cur:
                    pygame.draw.rect(s, GREEN, (x, r.bottom + 2, b, 5))
                x += b
            if einheit:
                f.text(s, einheit, (L.W // 2, y + 88), "xs", DIM, "center")
        f.text(s, "◀▶ Stelle  ·  ▲▼ ändern  ·  OK Start  ·  ZURÜCK", (L.W // 2, L.H - 18), "xs", DIM, "center")


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
        f.text(s, f"ZEIT  ·  {mmss(self.limit)}", (L.W // 2, L.y(46)), "l", INK, "center")
        if self.phase == "countdown":
            n = COUNTDOWN - int(now - self.t0)
            if n <= 0:
                self.phase, self.start = "laeuft", now
                self.app.play("los")
                return
            self.ton(n)
            f.text(s, str(n), (L.W // 2, L.y(280)), "xl", INK, "center")
            f.text(s, "bereit machen", (L.W // 2, L.y(370)), "m", DIM, "center")
            return
        rest = self.limit - (now - self.start)
        if self.phase == "laeuft" and rest <= 0:
            self.phase, self.ende = "nachlauf", self.start + self.limit
            self.app.play("ende")
        if self.phase == "nachlauf":
            if now - self.ende > 0.6:
                st = auswerten(self.punches, self.limit) | dict(disz="ZEIT", ziel=self.limit)
                self.app.replace(Stats(self.app, st), 0.4)
            f.text(s, "ZEIT!", (L.W // 2, L.y(170)), "xl", GREEN, "center")
        else:
            letzte = rest <= COUNTDOWN
            letzte and self.ton(math.ceil(rest))
            f.text(s, str(math.ceil(rest)) if letzte else f"{rest:.1f}", (L.W // 2, L.y(170)), "xl", ROT if letzte else GREEN,
                   "center")
            balken(s, L.y(230), 1 - rest / self.limit)
        zaehler(s, f, [r for r in self.punches if r["ok"]], L.y(350))
        f.text(s, "ZURÜCK  abbrechen", (L.W // 2, L.H - 18), "xs", DIM, "center")


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
        f.text(s, f"SCHLÄGE  ·  {self.ziel}", (L.W // 2, L.y(46)), "l", INK, "center")
        n = sum(r["ok"] for r in self.punches)
        if self.dauer is not None:
            self.t_ende = self.t_ende or now
            if now - self.t_ende > 1.5:
                st = auswerten(self.punches, self.dauer) | dict(disz="SCHLÄGE", ziel=self.ziel)
                return self.app.replace(Stats(self.app, st), 0.4)
            uhr, col = self.dauer, GREEN
        elif self.start is None:
            uhr, col = 0.0, DIM
            f.text(s, "Los geht's mit dem ersten Schlag", (L.W // 2, L.y(250)), "s", DIM, "center")
        else:
            uhr, col = now - self.start, INK
        f.text(s, f"{uhr:.2f}", (L.W // 2, L.y(160)), "xl", col, "center")
        balken(s, L.y(220), min(1, n / self.ziel))
        zaehler(s, f, [r for r in self.punches if r["ok"]], L.y(350), f"{n} / {self.ziel}")
        f.text(s, "ZURÜCK  abbrechen", (L.W // 2, L.H - 18), "xs", DIM, "center")


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
        f.text(s, "REAKTION", (L.W // 2, L.y(46)), "l", INK, "center")
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
        f.text(s, f"RUNDE {k} / {self.runden}  ·  KOMBO {self.kombo}", (L.W // 2, L.y(110)), "s", DIM, "center")
        if self.phase == "jetzt":
            r = pygame.draw.rect(s, GREEN, (L.W // 2 - 260, L.y(170), 520, L.y(220)))
            f.text(s, "JETZT!", (L.W // 2, r.centery - 20), "xl", BG, "center")
            if self.kombo > 1:
                f.text(s, f"{len(self.treffer)} / {self.kombo}", (L.W // 2, r.centery + 70), "m", BG, "center")
        elif self.phase == "anzeige":
            gut = self.msg.endswith("ms")
            f.text(s, self.msg, (L.W // 2, L.y(280)), "xl", GREEN if gut else ROT, "center")
        else:
            f.text(s, "warten …", (L.W // 2, L.y(280)), "l", DIM, "center")
        gut = [t for _, t in self.zeiten if t is not None]
        if gut:
            f.text(s, f"Ø {_mittel(gut) * 1000:.0f} ms  ·  beste {min(gut) * 1000:.0f} ms  ·  Fehlstarts {self.fehlstart}",
                   (L.W // 2, L.y(470)), "s", DIM, "center")
        f.text(s, "ZURÜCK  abbrechen", (L.W // 2, L.H - 18), "xs", DIM, "center")

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
        f.text(s, "REAKTIONSZEITEN", (L.W // 2, L.y(46)), "l", INK, "center")
        r = graf_rect()
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
        kennzahlen(s, f, [(name, f"{wert * 1000 * k:.0f}", col, "ms", "l") for name, wert, col in
                          (("Ø", st["r_avg"], INK), ("BESTE", st["r_best"], GREEN))]
                   + [("FEHLSTARTS", str(st["fehlstart"]), ROT if st["fehlstart"] else INK, "", "l")], r.bottom + 30)
        f.text(s, f"KOMBO {st['kombo']}  ·  {st['ziel']} RUNDEN", (r.centerx, r.bottom + 30), "s", DIM, "center")
        f.text(s, "OK  speichern oder verwerfen", (L.W // 2, L.H - 18), "xs", DIM, "center")


def balken(s, y, k, h=12):
    w = min(600, L.W - 80)
    pygame.draw.rect(s, LO, ((L.W - w) // 2, y, w, h), 1)
    pygame.draw.rect(s, GREEN, ((L.W - w) // 2, y, int(w * k), h))


def zeit(app):
    return Setup(app, "ZEIT", [("ZEITLIMIT", "zeit_limit", UHR, "min : s")], Zeit)


def serie(app):
    return Setup(app, "SCHLÄGE", [("SCHLAGANZAHL", "serie_n", (10, 10, 10), "")], Serie)


def reaktion(app):
    return Setup(app, "REAKTION", [("RUNDEN", "reak_runden", (10, 10), ""),
                                   ("SCHLÄGE PRO KOMBO", "reak_kombo", (10,), "")], Reaktion)
