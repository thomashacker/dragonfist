import json
import math
import random
import time

import pygame

from runlog import schreiben
from scenes import L, BG, INK, DIM, LO, GREEN, SPIEL, Scene, Tiles

BLAU = (90, 160, 255)
def _ms(v):
    return f"{v * 1000:.0f}"


def kmh(e, k="v_avg"):
    return f"{e[k]:.1f}" if e.get(k) else "–"


def _reak(e):
    return e["r_avg"] + STRAFE_S * e.get("fehlstart", 0)


# Spalten (Titel, x, Wert) und Sortierung je Disziplin; besser = kleinerer Schlüssel
DISZIPLINEN = {
    "TRAINING": ((("Ø KM/H", 400, kmh), ("TOP", 520, lambda e: kmh(e, "v_max")),
                  ("SCHLÄGE", 640, lambda e: str(e["n"])), ("ZEIT", 780, lambda e: mmss(e["dauer"]))),
                 lambda e: (-(e.get("v_avg") or 0), -e["n"])),
    "ZEIT": ((("SCHLÄGE", 400, lambda e: str(e["n"])), ("PRO S", 520, lambda e: f"{e['takt_avg']:.2f}"),
              ("Ø KM/H", 640, kmh), ("TOP", 760, lambda e: kmh(e, "v_max"))),
             lambda e: (-e["n"], -(e.get("v_avg") or 0))),
    "SCHLÄGE": ((("ZEIT", 400, lambda e: f"{e['dauer_s']:.2f} s"), ("PRO S", 540, lambda e: f"{e['takt_avg']:.2f}"),
                 ("Ø KM/H", 660, kmh), ("TOP", 780, lambda e: kmh(e, "v_max"))),
                lambda e: (e["dauer_s"], -(e.get("v_avg") or 0))),
    "REAKTION": ((("WERTUNG", 400, lambda e: _ms(_reak(e))), ("Ø MS", 520, lambda e: _ms(e["r_avg"])),
                  ("FEHLST.", 640, lambda e: str(e.get("fehlstart", 0))), ("KOMBO", 760, lambda e: str(e["kombo"]))),
                 lambda e: (_reak(e), e["r_best"])),
    "PUNKTE": ((("PUNKTE", 400, lambda e: str(e["punkte"])), ("ZEIT", 540, lambda e: mmss(e["dauer"])),
                ("SCHLÄGE", 660, lambda e: str(e["n"])), ("MULTI", 780, lambda e: f"×{e['mult_max']}")),
               lambda e: (-e["punkte"], -e["dauer_s"])),
}
# Nur gleiche Einstellungen sind vergleichbar: je Ziel eine eigene Liste
GRUPPE = {"ZEIT": "{} S", "SCHLÄGE": "{} SCHLÄGE", "REAKTION": "{} RUNDEN"}
STRAFE_S = 0.1                 # Reaktion: jeder Fehlstart kostet so viel
MIN_TRAINING_S = 30            # kürzere Trainings stehen nur unter NEUESTE
MIN_TEMPO = 5                  # so viele gemessene Schläge braucht ein Tempo-Wert; TOP ist der zweitbeste
SEITE_S, ANIM_S = 6.5, 2.4
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
                v_avg=_mittel(hin) if len(hin) >= MIN_TEMPO else 0.0,
                vb_avg=_mittel(zur) if len(zur) >= MIN_TEMPO else 0.0,
                v_max=sorted(hin)[-2] if len(hin) >= MIN_TEMPO else 0.0, v_n=len(hin), wege=wege,
                genau=100 * (1 - 2 * _mittel(mitte)) if mitte else 0.0, streu=streu)


def laden(datei):
    """Kaputte Datei wird beiseitegelegt statt beim nächsten Speichern überschrieben."""
    try:
        return json.loads(datei.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except ValueError:
        datei.replace(datei.with_name(f"{datei.stem}.kaputt-{int(time.time())}{datei.suffix}"))
        return {}


def eintragen(datei, disz, e):
    d = laden(datei)
    d.setdefault(disz, []).append(e)
    schreiben(datei, d)


def rangliste(datei, disz):
    return sorted(laden(datei).get(disz, []), key=DISZIPLINEN[disz][1])


def listen(d):
    """Alle Highscore-Listen als (Disziplin, Ziel); Ziel None = eine Liste für die ganze Disziplin."""
    out = []
    for disz in DISZIPLINEN:
        ziele = sorted({e.get("ziel") for e in d.get(disz, [])} - {None}) if disz in GRUPPE else []
        out += [(disz, z) for z in ziele] or [(disz, None)]
    return out


def wertung(d, disz, ziel):
    """Alle Einträge einer Liste und die gewerteten: beste zuerst, je Name nur der beste."""
    alle = sorted((e for e in d.get(disz, []) if ziel is None or e.get("ziel") == ziel), key=DISZIPLINEN[disz][1])
    gut = [e for e in alle if disz != "TRAINING" or e["dauer"] >= MIN_TRAINING_S]
    namen = set()
    return alle, [e for e in gut if not (e["name"] in namen or namen.add(e["name"]))]


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


def graf_rect():
    return pygame.Rect(70, L.y(150), L.W - 100, 340) if L.hoch else pygame.Rect(110, 130, 600, 340)


def kennzahlen(s, f, items, unter):
    """Kennzahlen neben der Grafik, hochkant in zwei Spalten darunter: (Titel, Wert, Farbe, Einheit, Schrift)."""
    schritt = 160 if any(it[4] == "xl" for it in items) else 110
    for i, (name, wert, col, einheit, gr) in enumerate(items):
        x, y = (40 + i % 2 * (L.W - 80) // 2, unter + 50 + i // 2 * 120) if L.hoch else (760, 140 + i * schritt)
        f.text(s, name, (x, y), "s", DIM)
        r = f.text(s, wert, (x, y + 26), gr, col)
        einheit and f.text(s, einheit, (r.right + 10, r.y + 20), "xs", DIM)


def zaehler(s, f, ok, y, gross=None):
    nl, v = sum(r["hand"] == "L" for r in ok), _mittel([r["v"] * 3.6 for r in ok if r["v"]])
    f.text(s, gross or str(len(ok)), (L.W // 2, y), "xl", INK, "center")
    f.text(s, f"Schläge  ·  links {nl}  ·  rechts {len(ok) - nl}  ·  Ø {v:.1f} km/h", (L.W // 2, y + 70), "s", DIM,
           "center")


class Training(Scene):
    music, leds, sounds, bare = "action", "spiel", SPIEL, True

    def __init__(self, app):
        super().__init__(app)
        self.t0, self.punches, self.last = None, [], None

    def punch(self, r):
        if self.t0 is not None:
            self.punches.append(r | {"t": r["t"] - self.t0})
            if r["v"]:
                self.last = r

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
        f.text(s, "TRAINING", (L.W // 2, L.y(50)), "l", INK, "center")
        f.text(s, mmss(now - self.t0), (L.W // 2, L.y(190)), "xl", INK, "center")
        zaehler(s, f, [r for r in self.punches if r["ok"]], L.y(345))
        r = self.last
        f.text(s, f"{r['v'] * 3.6:.1f} km/h" if r else "–", (L.W // 2, L.y(495)), "m",
               GREEN if r and now - r["t"] < 2 else DIM, "center")
        f.text(s, "ZURÜCK  Training beenden", (L.W // 2, L.H - 18), "xs", DIM, "center")


class Stats(Scene):
    bare = True
    TITEL = ("ZEIT", "SCHLÄGE", "SCHLÄGE PRO SEKUNDE", "GESCHWINDIGKEIT", "GENAUIGKEIT")

    def __init__(self, app, st):
        super().__init__(app)
        self.st, self.t0, self.seite, self.ziel, self.auto = st, None, -1, None, True
        self.seiten = (self.zeit, self.schlaege, self.takt, self.tempo, self.weg)
        rnd = random.Random(1)
        self.jitter = [(rnd.uniform(-0.012, 0.012), rnd.uniform(-0.012, 0.012)) for _ in st["wege"]]

    def on(self, a):
        if a in ("left", "right"):
            jetzt = max(self.seite, 0) if self.ziel is None else self.ziel
            self.ziel = (jetzt + (1 if a == "right" else -1)) % len(self.seiten)
        elif a in ("ok", "back"):
            self.app.play("ok")
            self.app.push(Wahl(self.app, self.st))

    def draw(self, s, now):
        if self.t0 is None:
            self.t0 = now
        if self.ziel is not None:
            self.t0, self.auto = now, False
        u = now - self.t0
        i = int(u // SEITE_S) % len(self.seiten) if self.auto else self.seite if self.ziel is None else self.ziel
        self.ziel = None
        if i != self.seite:
            self.seite = i
            self.app.play("move")
        k = min(1.0, (u % SEITE_S if self.auto else u) / ANIM_S)
        k = 1 - (1 - k) ** 3
        f = self.app.font
        f.text(s, self.TITEL[i], (L.W // 2, L.y(46)), "l", INK, "center")
        for j in range(len(self.seiten)):
            pygame.draw.circle(s, INK if j == i else LO, (L.W // 2 + (j - 2) * 22, L.y(90)), 5)
        self.seiten[i](s, f, k)
        f.text(s, "◀▶ blättern  ·  OK  speichern oder verwerfen", (L.W // 2, L.H - 18), "xs", DIM, "center")

    def zeit(self, s, f, k):
        if "punkte" in self.st:
            f.text(s, f"{round(self.st['punkte'] * k)} PUNKTE", (L.W // 2, L.y(200)), "xl", GREEN, "center")
            f.text(s, f"bis × {self.st['mult_max']}", (L.W // 2, L.y(470)), "m", DIM, "center")
        f.text(s, mmss(self.st["dauer"] * k), (L.W // 2, L.y(290)), "xl", INK, "center")
        f.text(s, f"{self.st['n']} Schläge  ·  {self.st['fehl']} Fehlschläge", (L.W // 2, L.y(400)), "m", DIM, "center")

    def schlaege(self, s, f, k):
        st = self.st
        f.text(s, str(round(st["n"] * k)), (L.W // 2, L.y(250)), "xl", INK, "center")
        f.text(s, "Schläge", (L.W // 2, L.y(320)), "m", DIM, "center")
        r, links = pygame.Rect(L.W // 2 - 220, L.y(380), 440, 10), st["nl"] / max(st["n"], 1)
        pygame.draw.rect(s, LO, r)
        pygame.draw.rect(s, DIM, (r.x, r.y, int(r.w * links * k), r.h))
        f.text(s, f"links {st['nl']}", (r.x, r.bottom + 12), "xs", DIM)
        f.text(s, f"rechts {st['nr']}", (r.right, r.bottom + 12), "xs", DIM, "topright")
        f.text(s, f"Fehlschläge {st['fehl']}", (L.W // 2, L.y(480)), "s", DIM, "center")

    def takt(self, s, f, k):
        st, r = self.st, graf_rect()
        ymax = max(st["takt_max"] * 1.15, 0.5)
        _achse(f, s, r, ymax, mmss(st["dauer"]))
        _kurve(s, r, st["takt"], ymax, GREEN, k)
        _strich(s, r, st["takt_avg"], ymax, INK, k)
        kennzahlen(s, f, (("Ø", f"{st['takt_avg'] * k:.2f}", INK, "Schläge / s", "l"),
                     ("SPITZE", f"{st['takt_max'] * k:.2f}", GREEN, "", "l")), r.bottom)

    def tempo(self, s, f, k):
        st, r = self.st, graf_rect()
        ymax = max(st["hin"] + st["zur"] + [10]) * 1.1
        _achse(f, s, r, ymax, f"{st['n']} Schläge")
        for werte, col in ((st["hin"], GREEN), (st["zur"], BLAU)):
            if len(werte) > 10:
                _kurve(s, r, werte, ymax, _dunkel(col), k, 1)
            _kurve(s, r, _glatt(werte), ymax, col, k)
        _strich(s, r, st["v_avg"], ymax, GREEN, k)
        _strich(s, r, st["vb_avg"], ymax, BLAU, k)
        kennzahlen(s, f, [(name, f"{v * k:.1f}", col, "km/h", "l") for name, v, col in
                     (("HIN  Ø", st["v_avg"], GREEN), ("ZURÜCK  Ø", st["vb_avg"], BLAU), ("TOP", st["v_max"], INK))],
              r.bottom)

    def weg(self, s, f, k):
        st, r = self.st, graf_rect().inflate(-40, -40)
        pygame.draw.rect(s, LO, r, 1)
        for j in range(0, r.h, 16):
            pygame.draw.line(s, DIM, (r.centerx, r.y + j), (r.centerx, r.y + j + 8), 1)
        f.text(s, "B  hinten", (r.x, r.y - 26), "xs", DIM)
        f.text(s, "A  vorne", (r.x, r.bottom + 8), "xs", DIM)
        m = math.ceil(len(st["wege"]) * k)
        for (hand, xa, xb), (ja, jb) in list(zip(st["wege"], self.jitter))[:m]:
            pygame.draw.line(s, _dunkel(GREEN) if k == 1 else GREEN, (r.x + (xa + ja) * r.w, r.bottom),
                             (r.x + (xb + jb) * r.w, r.y), 2)
        if k == 1:
            for hand in "LR":
                w = [(xa, xb) for h, xa, xb in st["wege"] if h == hand]
                if w:
                    xa, xb = _mittel([a for a, _ in w]), _mittel([b for _, b in w])
                    pygame.draw.line(s, GREEN, (r.x + xa * r.w, r.bottom), (r.x + xb * r.w, r.y), 7)
        streu = list(st["streu"].values())
        kennzahlen(s, f, (("ZUR MITTE", f"{st['genau'] * k:.0f}%", INK, "", "xl"),
                     ("STREUUNG", f"{_mittel(streu):.1f} %" if streu else "–", GREEN, "", "l")), r.bottom + 20)


class Wahl(Tiles):
    def __init__(self, app, st):
        self.title = f"{st.get('disz', 'TRAINING')} BEENDET"
        super().__init__(app, [("SPEICHERN", "Name wählen", lambda: app.push(namen_wahl(app, st))),
                               ("VERWERFEN", "zurück zum Menü", lambda: app.home())])


def speichern(app, st, name):
    disz = st.get("disz", "TRAINING")
    e = dict(id=int(time.time() * 1000), name=name, datum=time.strftime("%d.%m.%y"), dauer=round(st["dauer"]),
             dauer_s=round(st["dauer"], 2), n=st["n"], nl=st["nl"], nr=st["nr"], v_avg=round(st["v_avg"], 2),
             vb_avg=round(st["vb_avg"], 2), v_max=round(st["v_max"], 2), v_n=st.get("v_n", 0),
             takt_avg=round(st["takt_avg"], 3),
             genau=round(st["genau"], 1))
    e |= {k: st[k] for k in ("ziel", "kombo", "r_avg", "r_best", "fehlstart", "punkte", "mult_max") if k in st}
    eintragen(app.scores, disz, e)
    app.cfg["name"] = name
    app.save()
    app.home(Highscore(app, disz, e["id"], e.get("ziel") if disz in GRUPPE else None))


def bekannte_namen(datei):
    """Alle Namen aus den Highscores, zuletzt benutzte zuerst."""
    alle = sorted((e for liste in laden(datei).values() for e in liste), key=lambda e: -e["id"])
    return list(dict.fromkeys(e["name"] for e in alle))


def namen_wahl(app, st):
    namen = bekannte_namen(app.scores)
    return NamenWahl(app, st, namen) if namen else NameEntry(app, st)


class NamenWahl(Scene):
    bare = True

    def __init__(self, app, st, namen):
        super().__init__(app)
        self.st, self.items, self.sel = st, ["+ NEUER NAME"] + namen, 1

    def on(self, a):
        if a in ("up", "down", "left", "right"):
            self.sel = (self.sel + (1 if a in ("down", "right") else -1)) % len(self.items)
            self.app.play("move")
        elif a == "ok":
            self.app.play("ok")
            if self.sel == 0:
                self.app.push(NameEntry(self.app, self.st))
            else:
                speichern(self.app, self.st, self.items[self.sel])
        elif a == "back":
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "WER WAR'S?", (L.W // 2, L.y(54)), "l", INK, "center")
        y0 = L.y(110)
        n = (L.H - y0 - 60) // 58
        von = min(max(0, self.sel - n // 2), max(0, len(self.items) - n))
        self.ziele = []
        for j, name in enumerate(self.items[von:von + n]):
            k = von + j
            r = pygame.Rect(L.W // 2 - 260, y0 + j * 58, 520, 50)
            self.ziele.append((k, r))
            on = k == self.sel
            pygame.draw.rect(s, INK, r) if on else pygame.draw.rect(s, LO, r, 1)
            f.text(s, name, r.center, "m", BG if on else (DIM if k == 0 else INK), "center")
        x = min(L.W // 2 + 300, L.W - 14)
        von and f.text(s, "▲", (x, y0 + 25), "s", DIM, "center")
        von + n < len(self.items) and f.text(s, "▼", (x, y0 + (n - 1) * 58 + 25), "s", DIM, "center")
        f.text(s, "▲▼ wählen  ·  OK speichern  ·  ZURÜCK", (L.W // 2, L.H - 18), "xs", DIM, "center")


EINZUG = (0, 0, 0.5, 0, 0)
TASTEN = [[(c, c, 1) for c in "1234567890"], [(c, c, 1) for c in "QWERTZUIOP"], [(c, c, 1) for c in "ASDFGHJKL"],
          [(c, c, 1) for c in "YXCVBNM"] + [("⌫", "del", 3)], [("LEER", " ", 6), ("OK", "ok", 4)]]


class NameEntry(Scene):
    """Bildschirmtastatur: antippen oder mit dem Joystick wählen und OK; ROT löscht, bei leerem Namen zurück."""
    bare = True

    def __init__(self, app, st):
        super().__init__(app)
        self.st, self.name, self.zeile, self.sp = st, "", 2, 0
        self.tasten = [(z, i) for z, reihe in enumerate(TASTEN) for i in range(len(reihe))]

    @property
    def sel(self):
        return self.tasten.index((self.zeile, self.sp))

    @sel.setter
    def sel(self, k):
        self.zeile, self.sp = self.tasten[k]

    def _mitte(self, z, i):
        return EINZUG[z] + sum(w for _, _, w in TASTEN[z][:i]) + TASTEN[z][i][2] / 2

    def on(self, a):
        reihe = TASTEN[self.zeile]
        if a in ("left", "right"):
            self.sp = (self.sp + (1 if a == "right" else -1)) % len(reihe)
            self.app.play("move")
        elif a in ("up", "down"):
            x = self._mitte(self.zeile, self.sp)
            self.zeile = (self.zeile + (1 if a == "down" else -1)) % len(TASTEN)
            self.sp = min(range(len(TASTEN[self.zeile])), key=lambda i: abs(self._mitte(self.zeile, i) - x))
            self.app.play("move")
        elif a == "back":
            self.app.play("back")
            if not self.name:
                return self.app.pop()
            self.name = self.name[:-1]
        elif a == "ok":
            wert = reihe[self.sp][1]
            if wert == "ok":
                name = self.name.strip()
                if not name:
                    return self.app.play("back")
                self.app.play("ok")
                return speichern(self.app, self.st, name)
            if wert == "del":
                self.name = self.name[:-1]
            elif len(self.name) < NAME_LEN and (wert != " " or self.name):
                self.name += wert
            self.app.play("move")

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "NAME EINGEBEN", (L.W // 2, L.y(50)), "l", INK, "center")
        feld = pygame.Rect(L.W // 2 - 240, L.y(100), 480, 80)
        pygame.draw.rect(s, LO, feld, 3)
        strich = "_" if int(now * 2) % 2 and len(self.name) < NAME_LEN else ""
        f.text(s, self.name + strich if self.name or strich else " ", feld.center, "l", INK, "center")
        u = min(92, (L.W - 32) // 10)
        h = min(84, (L.H - feld.bottom - 80) // len(TASTEN))
        x0, y0 = (L.W - 10 * u) // 2, feld.bottom + max(30, (L.H - feld.bottom - 50 - h * len(TASTEN)) // 2)
        self.ziele = []
        for z, reihe in enumerate(TASTEN):
            x = x0 + EINZUG[z] * u
            for i, (label, _, w) in enumerate(reihe):
                r = pygame.Rect(x + 3, y0 + z * h + 3, w * u - 6, h - 6)
                x += w * u
                self.ziele.append((len(self.ziele), r))
                on = (z, i) == (self.zeile, self.sp)
                pygame.draw.rect(s, INK, r) if on else pygame.draw.rect(s, LO, r, 2)
                f.text(s, label, r.center, "m", BG if on else INK, "center")
        f.text(s, "tippen oder ◀▶▲▼ + OK  ·  ROT löscht", (L.W // 2, L.H - 18), "xs", DIM, "center")


class Highscore(Scene):
    """▲▼ blättert, OK/Gelb wechselt zwischen BESTE (je Name der beste) und NEUESTE, ◀▶ wechselt die Liste."""
    bare, ZEILE = True, 44

    def __init__(self, app, disz="TRAINING", neu=None, ziel=None):
        super().__init__(app)
        self.wahl, self.neu, self.oben, self.neueste, self.n = (disz, ziel), neu, 0, False, 1
        self.zeigen_neu, self.listen = neu is not None, []

    def liste(self):
        try:
            stand = self.app.scores.stat().st_mtime_ns
        except OSError:
            stand = None
        if getattr(self, "_key", None) != (self.wahl, self.neueste, stand):
            d = laden(self.app.scores)
            self.listen = listen(d)
            if self.wahl not in self.listen:
                self.wahl = next((k for k in self.listen if k[0] == self.wahl[0]), self.listen[0])
            alle, beste = wertung(d, *self.wahl)
            rang = {e["id"]: i for i, e in enumerate(beste, 1)}
            zeigen = sorted(alle, key=lambda e: -e["id"]) if self.neueste else beste
            self._key, self._liste = (self.wahl, self.neueste, stand), [(rang.get(e["id"], "–"), e) for e in zeigen]
        return self._liste

    def on(self, a):
        if a in ("left", "right"):
            self.liste()
            k = self.listen.index(self.wahl)
            self.wahl = self.listen[(k + (1 if a == "right" else -1)) % len(self.listen)]
            self.oben = 0
            self.app.play("move")
        elif a in ("up", "down"):
            self.oben = max(0, self.oben + (1 if a == "down" else -1))
            self.app.play("move")
        elif a in ("ok", "gelb"):
            self.neueste, self.oben = not self.neueste, 0
            self.app.play("ok")
        elif a == "back":
            self.app.play("back")
            self.app.pop()

    def draw(self, s, now):
        f = self.app.font
        f.text(s, "HIGHSCORE", (L.W // 2, L.y(46)), "l", INK, "center")
        liste = self.liste()
        disz, ziel = self.wahl
        tw = L.W // len(DISZIPLINEN)
        for i, d in enumerate(DISZIPLINEN):
            r = pygame.Rect(i * tw + 8, L.y(82), tw - 16, 36)
            on = d == disz
            pygame.draw.rect(s, INK, r) if on else pygame.draw.rect(s, LO, r, 1)
            f.text(s, d, r.center, "xs", BG if on else DIM, "center")
        if ziel is not None:
            f.text(s, "◀  " + GRUPPE[disz].format(f"{ziel:g}") + "  ▶", (L.W // 2, L.y(82) + 56), "s", GREEN, "center")
        hilfe = f"◀▶ Liste  ·  ▲▼ blättern  ·  OK {'BESTE' if self.neueste else 'NEUESTE'}  ·  ZURÜCK"
        f.text(s, hilfe, (L.W // 2, L.H - 16), "xs", DIM, "center")
        spalten = DISZIPLINEN[disz][0]
        if not liste:
            return f.text(s, "NOCH KEINE EINTRÄGE", (L.W // 2, L.y(300)), "m", DIM, "center")
        zeit = lambda e: time.strftime("%H:%M", time.localtime(e["id"] / 1000))
        if L.hoch:                                                     # schmal: ohne Datum, Werte kleiner
            kopf = (("#", 20, lambda e: ""), ("NAME", 72, lambda e: e["name"])) + tuple(
                (name, 240 + j * 90, wert) for j, (name, _, wert) in enumerate(spalten))
        else:
            kopf = (("#", 70, lambda e: ""), ("NAME", 120, lambda e: e["name"])) + spalten + (
                ("UHR", 890, zeit) if self.neueste else ("DATUM", 890, lambda e: e["datum"]),)
        klein, y0 = "xs" if L.hoch else "s", L.y(82) + 116
        for name, x, _ in kopf:
            f.text(s, name, (x, y0 - 32), "xs", DIM)
        self.n = n = max(1, (L.H - y0 - 70) // self.ZEILE)
        if self.zeigen_neu:
            self.zeigen_neu = False
            k = next((k for k, (_, e) in enumerate(liste) if e["id"] == self.neu), 0)
            self.oben = max(0, k - n // 2) if k >= n else 0
        self.oben = min(self.oben, max(0, len(liste) - n))
        for j, (i, e) in enumerate(liste[self.oben:self.oben + n]):
            y = y0 + j * self.ZEILE
            col = GREEN if e["id"] == self.neu else INK
            for name, x, wert in kopf[:2]:
                f.text(s, str(i) if name == "#" else wert(e), (x, y + 18), "m", col, "midleft")
            for name, x, wert in kopf[2:]:
                f.text(s, wert(e), (x, y + 18), klein, col, "midleft")
        f.text(s, f"{'ALLE, NEUESTE' if self.neueste else 'BESTE JE NAME'}  ·  {self.oben + 1}–{min(self.oben + n, len(liste))}"
                  f" von {len(liste)}", (L.W // 2, L.H - 44), "xs", GREEN, "center")
        if len(liste) > n:
            h, top = n * self.ZEILE, y0
            pygame.draw.rect(s, LO, (L.W - 8, top, 4, h))
            pygame.draw.rect(s, INK, (L.W - 8, top + h * self.oben // len(liste), 4, max(12, h * n // len(liste))))
