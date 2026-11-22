import json
import math
import random
import time

import pygame

from runlog import schreiben
from scenes import W, H, BG, INK, DIM, LO, GREEN, SPIEL, Scene, Tiles

BLAU, HAND = (90, 160, 255), {"L": (255, 150, 60), "R": (90, 170, 255)}
def _ms(v):
    return f"{v * 1000:.0f}"


# Spalten (Titel, x, Wert) und Sortierung je Disziplin; besser = kleinerer Schlüssel
DISZIPLINEN = {
    "TRAINING": ((("Ø KM/H", 400, lambda e: f"{e['v_avg']:.1f}"), ("MAX", 520, lambda e: f"{e['v_max']:.1f}"),
                  ("SCHLÄGE", 640, lambda e: str(e["n"])), ("ZEIT", 780, lambda e: mmss(e["dauer"]))),
                 lambda e: (-e["v_avg"], -e["n"])),
    "ZEIT": ((("SCHLÄGE", 400, lambda e: str(e["n"])), ("LIMIT", 520, lambda e: f"{e['ziel']} s"),
              ("PRO S", 640, lambda e: f"{e['takt_avg']:.2f}"), ("Ø KM/H", 780, lambda e: f"{e['v_avg']:.1f}")),
             lambda e: (-e["takt_avg"], -e["v_avg"])),
    "SCHLÄGE": ((("ZEIT", 400, lambda e: f"{e['dauer_s']:.2f} s"), ("SCHLÄGE", 540, lambda e: str(e["ziel"])),
                 ("PRO S", 660, lambda e: f"{e['takt_avg']:.2f}"), ("Ø KM/H", 780, lambda e: f"{e['v_avg']:.1f}")),
                lambda e: (-e["takt_avg"], -e["v_avg"])),
    "REAKTION": ((("Ø MS", 400, lambda e: _ms(e["r_avg"])), ("BESTE", 520, lambda e: _ms(e["r_best"])),
                  ("KOMBO", 640, lambda e: str(e["kombo"])), ("RUNDEN", 760, lambda e: str(e["ziel"]))),
                 lambda e: (e["r_avg"], e["r_best"])),
}
SEITE_S, ANIM_S = 6.5, 2.4
ALPHA = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
NAME_LEN = 8


def mmss(s):
    s = int(s)
    return f"{s // 60:02d}:{s % 60:02d}"


def _mittel(v):
    return sum(v) / len(v) if v else 0.0


def _lage(m, lo, n):
    idx = [i - lo for i in range(lo, lo + n) if m >> i & 1]
    return (_mittel(idx) + 0.5) / n if idx else None


def auswerten(punches, dauer, n_a=6, n_ch=13):
    """punches: Ergebnisse aus Punch.tick mit t relativ zum Start."""
    dauer = max(dauer, 1e-3)
    ok = [r for r in punches if r["ok"]]
    n = len(ok)
    b = max(2, math.ceil(dauer / 30))
    takt = [0.0] * max(1, math.ceil(dauer / b))
    for r in ok:
        takt[min(len(takt) - 1, int(r["t"] // b))] += 1 / b
    hin = [r["v"] * 3.6 for r in ok if r["v"]]
    zur = [r["vb"] * 3.6 for r in ok if r.get("vb")]
    wege = [(r["hand"], xa, xb) for r in ok
            for xa, xb in [(_lage(r["am"], 0, n_a), _lage(r["bm"], n_a, n_ch - n_a))] if xa is not None and xb is not None]
    streu = {}
    for h in "LR":
        x = [(xa + xb) / 2 for hh, xa, xb in wege if hh == h]
        if len(x) > 1:
            m = _mittel(x)
            streu[h] = 100 * _mittel([(v - m) ** 2 for v in x]) ** 0.5
    mitte = [abs((xa + xb) / 2 - 0.5) for _, xa, xb in wege]
    return dict(dauer=dauer, n=n, nl=sum(r["hand"] == "L" for r in ok), nr=sum(r["hand"] == "R" for r in ok),
                fehl=len(punches) - n, takt=takt, takt_avg=n / dauer, takt_max=max(takt), hin=hin, zur=zur,
                v_avg=_mittel(hin), vb_avg=_mittel(zur), v_max=max(hin, default=0.0), wege=wege,
                genau=100 * (1 - 2 * _mittel(mitte)) if mitte else 0.0, streu=streu)


def laden(datei):
    try:
        return json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def eintragen(datei, disz, e):
    d = laden(datei)
    d.setdefault(disz, []).append(e)
    schreiben(datei, d)


def rangliste(datei, disz):
    return sorted(laden(datei).get(disz, []), key=DISZIPLINEN[disz][1])


def _kurve(s, r, werte, ymax, col, k, w=3):
    if not werte:
        return
    n = len(werte)
    pts = [(r.x + (i / (n - 1) if n > 1 else 0.5) * r.w, r.bottom - min(v / ymax, 1) * r.h) for i, v in enumerate(werte)]
    m = max(1, math.ceil(n * k))
    if m > 1:
        pygame.draw.lines(s, col, False, pts[:m], w)
    for p in pts[:m] if n < 40 else pts[m - 1:m]:
        pygame.draw.circle(s, col, p, w + 1)


def _glatt(v, n=5):
    return [_mittel(v[max(0, i - n // 2):i + n // 2 + 1]) for i in range(len(v))] if len(v) > 2 * n else v


def _dunkel(c):
    return tuple(x // 3 for x in c)


def _strich(s, r, v, ymax, col, k):
    y = r.bottom - min(v / ymax, 1) * r.h
    for x in range(r.x, r.x + int(r.w * k), 18):
        pygame.draw.line(s, col, (x, y), (min(x + 10, r.right), y), 2)


def _achse(f, s, r, ymax, unten):
    pygame.draw.rect(s, LO, r, 1)
    f.text(s, f"{ymax:.0f}" if ymax >= 10 else f"{ymax:.1f}", (r.x - 10, r.y), "xs", DIM, "topright")
    f.text(s, "0", (r.x - 10, r.bottom), "xs", DIM, "bottomright")
    f.text(s, unten, (r.right, r.bottom + 8), "xs", DIM, "topright")


class Training(Scene):
    music, leds, sounds, bare = "action", "spiel", SPIEL, True

    def __init__(self, app):
        super().__init__(app)
        self.t0, self.punches, self.last = None, [], {}

    def punch(self, r):
        if self.t0 is not None:
            self.punches.append(r | {"t": r["t"] - self.t0})
            if r["v"]:
                self.last[r["hand"]] = r

    def on(self, a):
        if a != "back":
            return
        self.app.play("back")
        if not any(r["ok"] for r in self.punches):
            return self.app.pop()
        self.app.replace(Stats(self.app, auswerten(self.punches, time.monotonic() - (self.t0 or 0))), 0.4)

    def draw(self, s, now):
        if self.t0 is None:
            self.t0 = now
        f = self.app.font
        f.text(s, "TRAINING", (W // 2, 50), "l", INK, "center")
        f.text(s, mmss(now - self.t0), (W // 2, 190), "xl", INK, "center")
        ok = [r for r in self.punches if r["ok"]]
        for hand, x, name in (("L", W // 4, "LINKS"), ("R", 3 * W // 4, "RECHTS")):
            f.text(s, name, (x, 300), "s", HAND[hand], "center")
            f.text(s, str(sum(r["hand"] == hand for r in ok)), (x, 360), "xl", INK, "center")
            r = self.last.get(hand)
            frisch = r and now - r["t"] < 2
            f.text(s, f"{r['v'] * 3.6:.1f} km/h" if r else "–", (x, 440), "m", GREEN if frisch else DIM, "center")
        v = _mittel([r["v"] * 3.6 for r in ok if r["v"]])
        f.text(s, f"GESAMT {len(ok)}  ·  Ø {v:.1f} km/h", (W // 2, 510), "s", DIM, "center")
        f.text(s, "ZURÜCK  Training beenden", (W // 2, H - 18), "xs", DIM, "center")


class Stats(Scene):
    bare = True
    TITEL = ("ZEIT", "SCHLÄGE", "SCHLÄGE PRO SEKUNDE", "GESCHWINDIGKEIT", "GENAUIGKEIT")

    def __init__(self, app, st):
        super().__init__(app)
        self.st, self.t0, self.seite = st, None, -1
        self.seiten = (self.zeit, self.schlaege, self.takt, self.tempo, self.weg)
        rnd = random.Random(1)
        self.jitter = [(rnd.uniform(-0.012, 0.012), rnd.uniform(-0.012, 0.012)) for _ in st["wege"]]

    def on(self, a):
        if a in ("ok", "back"):
            self.app.play("ok")
            self.app.push(Wahl(self.app, self.st))

    def draw(self, s, now):
        if self.t0 is None:
            self.t0 = now
        u = now - self.t0
        i = int(u // SEITE_S) % len(self.seiten)
        if i != self.seite:
            self.seite = i
            self.app.play("move")
        k = min(1.0, (u % SEITE_S) / ANIM_S)
        k = 1 - (1 - k) ** 3
        f = self.app.font
        f.text(s, self.TITEL[i], (W // 2, 46), "l", INK, "center")
        for j in range(len(self.seiten)):
            pygame.draw.circle(s, INK if j == i else LO, (W // 2 + (j - 2) * 22, 90), 5)
        self.seiten[i](s, f, k)
        f.text(s, "OK  speichern oder verwerfen", (W // 2, H - 18), "xs", DIM, "center")

    def zeit(self, s, f, k):
        f.text(s, mmss(self.st["dauer"] * k), (W // 2, 290), "xl", INK, "center")
        f.text(s, f"{self.st['n']} Schläge  ·  {self.st['fehl']} Fehlschläge", (W // 2, 400), "m", DIM, "center")

    def schlaege(self, s, f, k):
        st = self.st
        f.text(s, str(round(st["n"] * k)), (W // 2, 200), "xl", INK, "center")
        for j, (hand, name) in enumerate((("L", "LINKS"), ("R", "RECHTS"))):
            y, v = 320 + j * 70, st["n" + hand.lower()]
            f.text(s, name, (300, y), "m", HAND[hand], "midright")
            pygame.draw.rect(s, LO, (330, y - 18, 440, 36), 1)
            pygame.draw.rect(s, HAND[hand], (330, y - 18, int(440 * v / max(st["n"], 1) * k), 36))
            f.text(s, str(round(v * k)), (800, y), "m", INK, "midleft")
        f.text(s, f"Fehlschläge {st['fehl']}", (W // 2, 480), "s", DIM, "center")

    def takt(self, s, f, k):
        st, r = self.st, pygame.Rect(110, 130, 600, 340)
        ymax = max(st["takt_max"] * 1.15, 0.5)
        _achse(f, s, r, ymax, mmss(st["dauer"]))
        _kurve(s, r, st["takt"], ymax, GREEN, k)
        _strich(s, r, st["takt_avg"], ymax, INK, k)
        f.text(s, "Ø", (760, 170), "s", DIM)
        f.text(s, f"{st['takt_avg'] * k:.2f}", (760, 196), "l", INK)
        f.text(s, "Schläge / s", (760, 250), "s", DIM)
        f.text(s, "SPITZE", (760, 320), "s", DIM)
        f.text(s, f"{st['takt_max'] * k:.2f}", (760, 346), "l", GREEN)

    def tempo(self, s, f, k):
        st, r = self.st, pygame.Rect(110, 130, 600, 340)
        ymax = max(st["hin"] + st["zur"] + [10]) * 1.1
        _achse(f, s, r, ymax, f"{st['n']} Schläge")
        for werte, col in ((st["hin"], GREEN), (st["zur"], BLAU)):
            if len(werte) > 10:
                _kurve(s, r, werte, ymax, _dunkel(col), k, 1)
            _kurve(s, r, _glatt(werte), ymax, col, k)
        _strich(s, r, st["v_avg"], ymax, GREEN, k)
        _strich(s, r, st["vb_avg"], ymax, BLAU, k)
        for y, name, v, col in ((140, "HIN  Ø", st["v_avg"], GREEN), (250, "ZURÜCK  Ø", st["vb_avg"], BLAU),
                                (360, "MAX", st["v_max"], INK)):
            f.text(s, name, (760, y), "s", DIM)
            f.text(s, f"{v * k:.1f}", (760, y + 26), "l", col)
            f.text(s, "km/h", (760 + f.f["l"].size(f"{v:.1f}")[0] + 10, y + 46), "xs", DIM)

    def weg(self, s, f, k):
        st, r = self.st, pygame.Rect(110, 150, 560, 300)
        pygame.draw.rect(s, LO, r, 1)
        for j in range(0, r.h, 16):
            pygame.draw.line(s, DIM, (r.centerx, r.y + j), (r.centerx, r.y + j + 8), 1)
        f.text(s, "B  hinten", (r.x, r.y - 26), "xs", DIM)
        f.text(s, "A  vorne", (r.x, r.bottom + 8), "xs", DIM)
        m = math.ceil(len(st["wege"]) * k)
        for (hand, xa, xb), (ja, jb) in list(zip(st["wege"], self.jitter))[:m]:
            pygame.draw.line(s, _dunkel(HAND[hand]) if k == 1 else HAND[hand], (r.x + (xa + ja) * r.w, r.bottom),
                             (r.x + (xb + jb) * r.w, r.y), 2)
        if k == 1:
            for hand in "LR":
                w = [(xa, xb) for h, xa, xb in st["wege"] if h == hand]
                if w:
                    xa, xb = _mittel([a for a, _ in w]), _mittel([b for _, b in w])
                    pygame.draw.line(s, HAND[hand], (r.x + xa * r.w, r.bottom), (r.x + xb * r.w, r.y), 7)
        f.text(s, "ZUR MITTE", (720, 160), "s", DIM)
        f.text(s, f"{st['genau'] * k:.0f}%", (720, 186), "xl", INK)
        f.text(s, "STREUUNG", (720, 320), "s", DIM)
        for j, hand in enumerate("LR"):
            v = st["streu"].get(hand)
            f.text(s, f"{hand}  {v:.1f} %" if v is not None else f"{hand}  –", (720, 350 + j * 36), "m", HAND[hand])


class Wahl(Tiles):
    def __init__(self, app, st):
        self.title = f"{st.get('disz', 'TRAINING')} BEENDET"
        super().__init__(app, [("SPEICHERN", "Name eingeben", lambda: app.push(NameEntry(app, st))),
                               ("VERWERFEN", "zurück zum Menü", lambda: app.home())])


class NameEntry(Scene):
    bare = True

    def __init__(self, app, st):
        super().__init__(app)
        name = app.cfg.get("name", "")[:NAME_LEN] or "A"
        self.st, self.pos = st, 0
        self.z = [c if c in ALPHA else " " for c in name.ljust(NAME_LEN)]

    def on(self, a):
        if a in ("up", "down"):
            self.z[self.pos] = ALPHA[(ALPHA.index(self.z[self.pos]) + (1 if a == "up" else -1)) % len(ALPHA)]
            self.app.play("move")
        elif a in ("left", "right"):
            self.pos = min(NAME_LEN - 1, max(0, self.pos + (1 if a == "right" else -1)))
            self.app.play("move")
        elif a == "back":
            self.app.play("back")
            self.app.pop()
        elif a == "ok":
            name = "".join(self.z).strip()
            if not name:
                return self.app.play("back")
            self.app.play("ok")
            st, disz = self.st, self.st.get("disz", "TRAINING")
            e = dict(id=int(time.time() * 1000), name=name, datum=time.strftime("%d.%m.%y"), dauer=round(st["dauer"]),
                     dauer_s=round(st["dauer"], 2), n=st["n"], nl=st["nl"], nr=st["nr"], v_avg=round(st["v_avg"], 2),
                     vb_avg=round(st["vb_avg"], 2), v_max=round(st["v_max"], 2), takt_avg=round(st["takt_avg"], 3),
                     genau=round(st["genau"], 1))
            e |= {k: st[k] for k in ("ziel", "kombo", "r_avg", "r_best", "fehlstart") if k in st}
            eintragen(self.app.scores, disz, e)
            self.app.cfg["name"] = name
            self.app.save()
            self.app.home(Highscore(self.app, disz, e["id"]))

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "NAME EINGEBEN", (W // 2, 70), "l", INK, "center")
        x0 = (W - NAME_LEN * 84) // 2
        for i, c in enumerate(self.z):
            r = pygame.Rect(x0 + i * 84, 230, 72, 96)
            on = i == self.pos
            pygame.draw.rect(s, INK, r) if on else pygame.draw.rect(s, LO, r, 3)
            f.text(s, c if c != " " else "·" if not on else "", r.center, "l", BG if on else INK, "center")
            if on:
                f.text(s, "▲", (r.centerx, r.y - 26), "s", INK, "center")
                f.text(s, "▼", (r.centerx, r.bottom + 26), "s", INK, "center")
        f.text(s, "▲▼ Buchstabe  ·  ◀▶ Stelle  ·  OK speichern  ·  ZURÜCK", (W // 2, H - 18), "xs", DIM, "center")


class Highscore(Scene):
    def __init__(self, app, disz="TRAINING", neu=None):
        super().__init__(app)
        self.sel, self.neu = list(DISZIPLINEN).index(disz), neu

    def on(self, a):
        if a in ("left", "right"):
            self.sel = (self.sel + (1 if a == "right" else -1)) % len(DISZIPLINEN)
            self.app.play("move")
        elif a in ("back", "ok"):
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "HIGHSCORE", (W // 2, 46), "l", INK, "center")
        tw = W // len(DISZIPLINEN)
        for i, d in enumerate(DISZIPLINEN):
            r = pygame.Rect(i * tw + 8, 82, tw - 16, 36)
            on = i == self.sel
            pygame.draw.rect(s, INK, r) if on else pygame.draw.rect(s, LO, r, 1)
            f.text(s, d, r.center, "xs", BG if on else DIM, "center")
        disz = list(DISZIPLINEN)[self.sel]
        liste, spalten = rangliste(self.app.scores, disz), DISZIPLINEN[disz][0]
        if not liste:
            return f.text(s, "NOCH KEINE EINTRÄGE", (W // 2, 300), "m", DIM, "center")
        kopf = (("#", 70, lambda e: ""), ("NAME", 120, lambda e: e["name"])) + spalten +             (("DATUM", 890, lambda e: e["datum"]),)
        for name, x, _ in kopf:
            f.text(s, name, (x, 140), "xs", DIM)
        zeilen = list(enumerate(liste[:8], 1))
        rang = next((i for i, e in enumerate(liste, 1) if e["id"] == self.neu), None)
        if rang and rang > 8:
            zeilen.append((rang, liste[rang - 1]))
        for j, (i, e) in enumerate(zeilen):
            y = 172 + j * 44
            col = GREEN if e["id"] == self.neu else INK
            for name, x, wert in kopf:
                f.text(s, str(i) if name == "#" else wert(e), (x, y + 18), "m" if x < 400 else "s", col, "midleft")
