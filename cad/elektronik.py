"""
Schrauben, Elektronik und Adern-Wege (build123d), dazu Verkabelungsplan und Pinliste.

Aufbau:
  - Pico (auf Schraubklemmen-Board) und Wago-Klemmen liegen im gedruckten Nest mittig
    zwischen A und B auf der unteren Sensorplatte. Ein gleiches Nest oben trägt nur Wagos.
  - Jede Ader läuft vom Sensorhalter durch den Einführschlitz in den Kabelkanal und darin
    zum Nest: rot -> Wago 5V, schwarz -> Wago GND, gelb (nur Empfänger) -> Pico-Pin.
  - Die Sender oben bekommen 5 V/GND über 2 Adern im hohlen hinteren linken Alu-Pfosten.
  - Raus gehen nur USB (zum Jetson) und 5 V vom Netzteil – hinten links über die Kante.

Platten-Koordinaten (lokal): wie modell.sensorplatte(), z=0 auf dem Brett.
Welt: unten (x, y, T+z), oben (-x, y, AUSSEN_H-T-z) – die obere Platte ist um Y gedreht.
"""
import functools
import itertools
import json
import math

import modell as M
import parameter as P
from modell import quader, stab, teil

T = M.T
W = P.FENSTER_BREITE
GPIO_FREI = list(range(0, 23)) + [26, 27, 28]

# Raspberry Pi Pico: physische Pins 1–20 (eine Seite) und 21–40 (andere Seite)
PICO_PINS = (["GP0", "GP1", "GND", "GP2", "GP3", "GP4", "GP5", "GND", "GP6", "GP7", "GP8", "GP9", "GND",
              "GP10", "GP11", "GP12", "GP13", "GND", "GP14", "GP15"] +
             ["GP16", "GP17", "GND", "GP18", "GP19", "GP20", "GP21", "GND", "GP22", "RUN", "GP26", "GP27", "GND",
              "GP28", "ADC_VREF", "3V3", "3V3_EN", "GND", "VSYS", "VBUS"])


def sensor_nr(xs, x, oben):
    """Nummer von links nach rechts in Weltlage (Sender oben heißen wie der Empfänger darunter)."""
    welt_x = sorted(-v if oben else v for v in xs)
    return welt_x.index(-x if oben else x) + 1


def welt(p, oben):
    x, y, z = p
    return (-x, y, M.AUSSEN_H - T - z) if oben else (x, y, T + z)


# ---------------------------------------------------------------------------
# Pinbelegung
# ---------------------------------------------------------------------------
def _reihe(pins_links_nach_rechts):
    """GPIO-Nummern einer Klemmreihe, von links (USB-Ende) nach rechts, ohne LED-Pin."""
    erg = []
    for pin in pins_links_nach_rechts:
        name = PICO_PINS[pin - 1]
        if name.startswith("GP") and int(name[2:]) not in P.GPIO_LED.values():
            erg.append(int(name[2:]))
    return erg


def pin_belegung():
    """Ebene A auf die vordere Klemmreihe (Pins 1–20), Ebene B auf die hintere (40–21),
    jeweils links nach rechts wie die Sensoren – so laufen die Adern nicht ums Board herum."""
    reihen = {"A": _reihe(range(1, 21)), "B": _reihe(range(40, 20, -1))}
    pins = []
    for ebene, xs in (("A", P.STRAHLEN_A), ("B", P.STRAHLEN_B)):
        if len(xs) > len(reihen[ebene]):
            raise ValueError(f"Ebene {ebene}: zu wenige GPIOs in der Klemmreihe")
        # gleichmäßig über die Reihe verteilen, damit jeder Sensor einen Pin nahe seiner x-Lage bekommt
        auswahl = [reihen[ebene][round(i * (len(reihen[ebene]) - 1) / max(len(xs) - 1, 1))] for i in range(len(xs))]
        for x, gp in zip(sorted(xs), auswahl):
            seite = "links" if x < 0 else ("rechts" if x > 0 else "Mitte")
            pins.append({"gpio": gp, "pin": PICO_PINS.index(f"GP{gp}") + 1, "ebene": ebene, "x_mm": x,
                         "seite": seite, "nr": len(pins) + 1})
    return pins


def pico_pin_ort(pin):
    """Lage der Schraubklemme eines Pico-Pins auf dem Board (lokal). USB-Ende links."""
    bx0, bx1, by0, by1 = M.nest_layout()["board"]
    schritt = (bx1 - bx0 - 12) / 19
    z = P.PLATTE_DICKE + P.NEST_BODEN + P.PICO_BOARD[2]
    if pin <= 20:
        return (bx0 + 6 + (pin - 1) * schritt, by0 + 4, z)
    return (bx0 + 6 + (40 - pin) * schritt, by1 - 4, z)


# ---------------------------------------------------------------------------
# Schrauben
# ---------------------------------------------------------------------------
def schraube(kopf, richtung, masse, name):
    """kopf: Mitte der Kopfunterseite, richtung: in den Werkstoff, masse: (d, Länge)."""
    d, l = masse
    dx, dy, dz = richtung
    spitze = (kopf[0] + dx * l, kopf[1] + dy * l, kopf[2] + dz * l)
    oben = (kopf[0] - dx * d * 0.7, kopf[1] - dy * d * 0.7, kopf[2] - dz * d * 0.7)
    return teil(stab(kopf, spitze, d) + stab(oben, kopf, 2 * d), name, "stahl")


def schrauben():
    teile = []
    dach = M.TASCHE_H + P.TURM_WAND
    ym = (M.Y_A + M.Y_B) / 2
    nest_z = P.PLATTE_DICKE + P.NEST_BODEN
    for oben in (False, True):
        wort, rz = ("oben", (0, 0, 1)) if oben else ("unten", (0, 0, -1))
        for y, xs in M.EBENEN:
            _, _, _, loch = M.gehaeuse_y(y, M.richtung(y))
            for x in xs:
                teile.append(schraube(welt((x, loch, dach), oben), rz, P.SCHRAUBE_SENSOR, f"Schraube Sensor {wort}"))
        for x in M.schraub_rippen():
            teile.append(schraube(welt((x, ym, P.PLATTE_DICKE), oben), rz, P.SCHRAUBE_GITTER,
                                  f"Schraube Gitter {wort}"))
        for x, y in M.nest_layout()["schrauben"]:
            teile.append(schraube(welt((x, y, nest_z), oben), rz, P.SCHRAUBE_GITTER, f"Schraube Nest {wort}"))
        dz = M.deckel_lage()[4] + P.DECKEL_DICKE
        for x, y in M.deckel_saeulen():
            teile.append(schraube(welt((x, y, dz), oben), rz, P.SCHRAUBE_SENSOR, f"Schraube Deckel {wort}"))
    kx0, kx1, ky0, ky1 = M.kabelkanal_lage()
    for z in (40, M.AUSSEN_H / 2 - 40, M.AUSSEN_H / 2 + 40, M.AUSSEN_H - 40):
        teile.append(schraube((kx1 - P.KABELKANAL_WAND, (ky0 + ky1) / 2, z), (1, 0, 0), P.SCHRAUBE_GITTER,
                              "Schraube Kabelkanal"))
    n = P.RAHMEN_SCHRAUBEN_JE_ECKE
    ys = [25 + i * (M.TIEFE - 50) / (n - 1) for i in range(n)] if n > 1 else [M.TIEFE / 2]
    for s in (-1, 1):
        for z in (T / 2, M.AUSSEN_H - T / 2):
            for y in ys:
                teile.append(schraube((s * (W / 2 + T), y, z), (-s, 0, 0), P.SCHRAUBE_RAHMEN, "Schraube Rahmen"))
    return teile


def schrauben_anzahl():
    zaehler = {}
    for t in schrauben():
        art = t.label.replace(" unten", "").replace(" oben", "")
        zaehler[art] = zaehler.get(art, 0) + 1
    return zaehler


# ---------------------------------------------------------------------------
# Wago-Belegung
# ---------------------------------------------------------------------------
def wago_bedarf():
    """Anzahl Wago 221-415 je Reihe {(seite, bus): k} für unten/oben und gesamt."""
    leiter = M.nest_leiter()
    erg = {pl: {key: M.wago_anzahl(n) for key, n in werte.items()} for pl, werte in leiter.items()}
    erg["gesamt"] = sum(sum(v.values()) for v in (erg["unten"], erg["oben"]))
    return erg


# ---------------------------------------------------------------------------
# Adern
# ---------------------------------------------------------------------------
def _strang(punkte, d, name, farbe):
    form = None
    for p0, p1 in zip(punkte, punkte[1:]):
        if math.dist(p0, p1) < 0.1:
            continue
        s = stab(p0, p1, d) + M.Pos(*p1) * M.Sphere(d / 2)
        form = s if form is None else form + s
    return teil(form, name, farbe)


# ---------------------------------------------------------------------------
# Kabelführung: rechtwinklig, jede Aderart auf eigener Höhe, damit sich nichts kreuzt.
# Wago-Einlässe zeigen nach außen (5V nach hinten, GND nach vorne), Board-Klemmen ebenso.
# ---------------------------------------------------------------------------
Z0 = P.PLATTE_DICKE + P.NEST_BODEN
Z_WAGO = Z0 + P.WAGO[2] / 2                 # Einlass der Wago
Z_PIN = Z0 + 6                               # Schraubklemme am Board
Z_BRUECKE = Z0 + 0.9                         # Brücke links <-> rechts, unter allen anderen
Z_UEBER = {1: Z0 + 11, -1: Z0 + 13}          # über die Wago-Reihen hinweg (Ebene A / B)
Z_ZULEITUNG, Z_LED, Z_USB, Z_LED_DATEN = Z0 + 15, Z0 + 17, Z0 + 20.5, Z0 + 22.5
Z_EINWURF = P.PLATTE_DICKE + 9.8             # Ader von oben in den Kanal gedrückt
Z_DICK = P.PLATTE_DICKE + 9.5                # USB und Netzteil im Kanal B, über den Sensoradern
Z_FLACH = P.PLATTE_DICKE + 2.5               # USB und Netzteil flach auf der Platte hinter dem Nest
SPUR = 1.6
TIEF = 8                                     # Ader steckt so tief im Einlass


def _abstand(a0, a1, b0, b1):
    """Kleinster Abstand zweier Strecken."""
    u, v, w = [p - q for p, q in zip(a1, a0)], [p - q for p, q in zip(b1, b0)], [p - q for p, q in zip(a0, b0)]
    a, b, c = sum(x * x for x in u), sum(x * y for x, y in zip(u, v)), sum(x * x for x in v)
    d, e = sum(x * y for x, y in zip(u, w)), sum(x * y for x, y in zip(v, w))
    n = a * c - b * b
    s = min(1, max(0, (b * e - c * d) / n)) if n > 1e-9 else 0
    t = min(1, max(0, (b * s + e) / c)) if c > 1e-9 else 0
    s = min(1, max(0, (b * t - d) / a)) if a > 1e-9 else 0
    return math.dist([p + s * x for p, x in zip(a0, u)], [p + t * x for p, x in zip(b0, v)])


class Verlegung:
    """Legt Adern nacheinander und nimmt je Ader die erste Variante, die keine andere berührt."""

    def __init__(self):
        self.strecken, self.eng = [], {}

    def _im_weg(self, p0, p1, d):
        lo = [min(a, b) for a, b in zip(p0, p1)]
        hi = [max(a, b) for a, b in zip(p0, p1)]
        for q0, q1, dq, qlo, qhi, wer in self.strecken:
            m = (d + dq) / 2 - 0.05
            if any(lo[i] - m > qhi[i] or hi[i] + m < qlo[i] for i in range(3)):
                continue
            if _abstand(p0, p1, q0, q1) < m:
                return wer
        return None

    def lege(self, name, d, varianten):
        erste, gruende = None, []
        for weg in varianten:
            weg = [p for i, p in enumerate(weg) if i == 0 or math.dist(p, weg[i - 1]) > 0.01]
            erste = erste or weg
            wer = next((w for w in (self._im_weg(a, b, d) for a, b in zip(weg, weg[1:])) if w), None)
            if wer is None:
                break
            gruende.append(wer)
        else:
            weg = erste
            self.eng[name] = sorted(set(gruende))
        for a, b in zip(weg, weg[1:]):
            self.strecken.append((a, b, d, [min(x, y) for x, y in zip(a, b)], [max(x, y) for x, y in zip(a, b)],
                                  name))
        return weg


def _raus(bus):
    return 1 if bus == "5V" else -1


def _einlaesse(sd, bus, n):
    """Aderenden in den nutzbaren Einlässen der Wago-Reihe (seite, bus) für n Adern, von innen nach außen.
    Zwischen benachbarten Wagos bleiben die Rand-Einlässe für die Kettenbrücke frei."""
    x0, _, y0, y1 = M.nest_layout()["wago"][(sd, bus)]
    k, wb, r = M.wago_anzahl(n), P.WAGO[0], _raus(bus)
    y = (y1 if r > 0 else y0) - r * (P.SPIEL + TIEF)
    xs = [x0 + P.SPIEL + j * wb + (e + 0.5) * (wb - 0.6) / 5
          for j in range(k) for e in range(5) if not (e == 4 and j < k - 1) and not (e == 0 and j)]
    return [(x, y, Z_WAGO) for x in sorted(xs, key=abs)]


def _pin_punkt(pin):
    """Aderende in der Schraubklemme eines Pico-Pins und Richtung nach außen."""
    x, y, _ = pico_pin_ort(pin)
    return (x, y, Z_PIN), (-1 if pin <= 20 else 1)


def _spuren(y, innen_zuerst=True):
    """Plätze (y, z) im Kanal an Ebene y, in der Reihenfolge der Vorliebe."""
    r = M.richtung(y)
    i0, i1 = M.kanal_y(y)
    spalten = [(i1 if r > 0 else i0) - r * (1.2 + SPUR * k) for k in range(7)]
    if not innen_zuerst:
        spalten.reverse()
    return [(cy, P.PLATTE_DICKE + 1 + SPUR * m) for m in range(3) for cy in spalten]


def _klemme_weg(ende, raus, r, cy, cz, z_ueber, versatz=0, aus=TIEF + 5):
    """Vom Platz (cy, cz) im Kanal zur Klemme: (x im Kanal, Punkte). Zeigt der Einlass vom Kanal weg,
    läuft die Ader auf z_ueber über die Reihe und kommt von der anderen Seite."""
    x = ende[0]
    if raus == -r:
        return x, [(x, cy, cz), (x, cy, ende[2]), ende]
    xk, yu = x + versatz, ende[1] + raus * aus
    return xk, [(xk, cy, cz), (xk, cy, z_ueber), (xk, yu, z_ueber), (x, yu, z_ueber), (x, yu, ende[2]), ende]


def _sensor_varianten(x, y, ai, ende, raus, flach=False):
    """Halter -> Einführschlitz -> Platz im Kanal -> Klemme. Adern, die über die Reihe steigen,
    liegen innen im Kanal: so kreuzt keine Einführung und kein Abgang ihren Aufstieg."""
    r = M.richtung(y)
    xs = x + (ai - 1) * 1.6
    ya = M.gehaeuse_y(y, r)[2] + r * (P.SPIEL + P.TURM_WAND)
    # erst gerade hinein; wenn kein Platz frei ist, im 8 mm breiten Schlitz seitlich ausweichen
    for dx in (0, 2.4, -2.4, 3.2, -3.2, 0.8, -0.8):
        for vs in ((3 * r,) if raus == -r else (3 * r, -3 * r, 5 * r, -5 * r)):
            for cy, cz in _spuren(y, raus != -r):
                _, rest = _klemme_weg(ende, raus, r, cy, cz, Z_UEBER[r], vs)
                for ze in ((cz, Z_EINWURF) if flach else (Z_EINWURF, cz)):
                    yield [(xs, ya, 3), (xs, ya, ze), (xs + dx, ya, ze), (xs + dx, cy, ze), (xs + dx, cy, cz)] + rest


def _abgang_varianten(ende, raus, y, z_ueber, x_ziel, aus=TIEF + 5, y_raus=None, versatz=3):
    """Klemme -> Platz im Kanal -> im Kanal bis x_ziel (-> durch den Schlitz hinaus bis y_raus)."""
    r = M.richtung(y)
    for cy, cz in _spuren(y):
        _, weg = _klemme_weg(ende, raus, r, cy, cz, z_ueber, versatz * r, aus)
        yield weg[::-1] + [(x_ziel, cy, cz)] + ([(x_ziel, y_raus, cz)] if y_raus is not None else [])


@functools.lru_cache(maxsize=None)
def _belegung(oben):
    """Welche Sensorader in welchen Einlass: ({(ebene, x, farbe): ziel}, {(seite, bus): freie Einlässe}).
    Die Sensoradern (feste Länge) bekommen die Einlässe, die ihrem Sensor in x am nächsten liegen, ohne
    sich zu überkreuzen; den Rest teilen sich Brücke, Zuleitung, Netzteil und LED (eigene Litze)."""
    ziele, rest = {}, {}
    for (sd, bus), n in M.nest_leiter()["oben" if oben else "unten"].items():
        plaetze = _einlaesse(sd, bus, n)
        sensoren = sorted(((x, e) for e, (_, xs) in zip("AB", M.EBENEN) for x in xs if M.seite(x) == sd),
                          key=lambda t: abs(t[0]))
        wahl = min(itertools.combinations(range(len(plaetze)), len(sensoren)),
                   key=lambda c: sorted((abs(abs(x) - abs(plaetze[i][0])) for (x, _), i in zip(sensoren, c)),
                                        reverse=True))
        for (x, ebene), i in zip(sensoren, wahl):
            ziele[(ebene, x, "rot" if bus == "5V" else "schwarz")] = plaetze[i]
        rest[(sd, bus)] = [q for i, q in enumerate(plaetze) if i not in wahl]
    return ziele, rest


def _rest_punkt(oben, sd, bus, nr):
    """Freier Einlass nr einer Wago-Reihe, von innen gezählt (Brücke, Zuleitung, Netzteil, GND, LED)."""
    return _belegung(oben)[1][(sd, bus)][nr]


ENGSTELLEN = {}


@functools.lru_cache(maxsize=None)
def adern_wege():
    """Alle Leitungen als Wege in Platten-Koordinaten:
    [{"name", "farbe", "d", "oben", "punkte"}]. Daraus entstehen 3D-Modell und 2D-Plan."""
    wege = []
    ENGSTELLEN.clear()
    pins = {(p["ebene"], p["x_mm"]): p for p in pin_belegung()}
    L = M.nest_layout()
    bx0, _, by0, by1 = L["board"]
    _, kb1 = M.kanal_y(M.Y_B)

    def dazu(v, name, farbe, d, oben, varianten, schwanz=()):
        wege.append({"name": name, "farbe": farbe, "d": d, "oben": oben,
                     "punkte": v.lege(name, d, varianten) + list(schwanz)})

    for oben in (False, True):
        v, wort = Verlegung(), "oben" if oben else "unten"
        leiter = M.nest_leiter()[wort]
        # Kettenbrücken zwischen benachbarten Wagos einer Reihe
        for (sd, bus), n in leiter.items():
            x0, _, y0, y1 = L["wago"][(sd, bus)]
            r, wb = _raus(bus), P.WAGO[0]
            yi = (y1 if r > 0 else y0) - r * (P.SPIEL + TIEF)
            ya = yi + r * (TIEF + 3.5)
            farbe = "rot" if bus == "5V" else "schwarz"
            for j in range(M.wago_anzahl(n) - 1):
                xa, xb = (x0 + P.SPIEL + (j + k) * wb + (e + 0.5) * (wb - 0.6) / 5 for k, e in ((0, 4), (1, 0)))
                dazu(v, f"Ader {farbe} Kette {bus} {sd} {wort} {j + 1}", farbe, 1.8, oben,
                     [[(xa, yi, Z_WAGO), (xa, ya, Z_WAGO), (xb, ya, Z_WAGO), (xb, yi, Z_WAGO)]])
        # Brücken zwischen linker und rechter Reihe: tief am Board vorbei (5V hinten, GND vorne)
        for farbe, bus, yb in (("rot", "5V", by1 + 4.5), ("schwarz", "GND", by0 - 4.5)):
            a, b = _rest_punkt(oben, "links", bus, 0), _rest_punkt(oben, "rechts", bus, 0)
            dazu(v, f"Ader {farbe} Brücke {bus} {wort}", farbe, 1.8, oben,
                 [[a, (a[0], yb, Z_WAGO), (a[0], yb, Z_BRUECKE), (b[0], yb, Z_BRUECKE), (b[0], yb, Z_WAGO), b]])
        if not oben:
            # Pico-GND an die linke GND-Reihe
            gnd, _ = _pin_punkt(PICO_PINS.index("GND") + 1)
            ziel = _rest_punkt(False, "links", "GND", 3)
            yq = by0 - 7
            dazu(v, "Ader schwarz Pico-GND", "schwarz", 1.4, False,
                 [[gnd, (gnd[0], yq, Z_PIN), (gnd[0], yq, Z_PIN + 2), (ziel[0], yq, Z_PIN + 2), (ziel[0], yq, Z_WAGO),
                   ziel]])
            # USB und Netzteil: im Kanal B oben an der Halterseite entlang zum Austritt hinten links,
            # dann um die Brettkante in den Kabelkanal außen. USB läuft darin nach oben ins Pult.
            import pult as PU                                  # spät: pult baut auf modell auf
            xa = M.austritt_x()
            kx, ky = M.kabelkanal_mitte()
            hinter = M.TIEFE + 12
            hoch = M.AUSSEN_H - T + 6                           # lokal: knapp über dem oberen Brett
            px, py, _ = PU.lage_auf_kiste()
            jx0, jx1, jy0, jy1, jz0, jz1 = PU.jetson_lage()
            pult_hinten = py + P.PULT_TIEFE + 8
            jz = M.AUSSEN_H - T + (jz0 + jz1) / 2               # Höhe der Jetson-Anschlüsse (lokal)
            netz = _rest_punkt(False, "links", "5V", 2)
            nx0 = L["aussen"][0]
            kb0 = M.kanal_y(M.Y_B)[0]
            ya_n, ya_u = kb0 - 13.6, kb0 - 8.6                  # zwei Bahnen zwischen Nest und Kanal B
            xe_n, xe_u = nx0 + 3.6, nx0 + 8.6                   # hier wechseln sie in den Kanal
            yk_n, yk_u = kb1 - 6.8, kb1 - 2.5
            dazu(v, "5-V-Netzteil -> Wago", "netz", 4, False,
                 [[netz, (netz[0], ya_n, Z_WAGO), (netz[0], ya_n, Z_FLACH), (xe_n, ya_n, Z_FLACH),
                   (xe_n, kb0 - 4.6, Z_FLACH), (xe_n, kb0 - 4.6, Z_DICK), (xe_n, yk_n, Z_DICK),
                   (xa - 2.2, yk_n, Z_DICK)]],
                 [(xa - 2.2, hinter, 10), (kx, hinter, 10), (kx, ky, 10), (kx, ky, -150)])
            ux, ym = bx0 - 2, L["ym"]
            ziel_x = px + jx0 + 20
            dazu(v, "USB-Kabel Pico -> Jetson", "usb", 4, False,
                 [[(ux, ym, P.PLATTE_DICKE + 8), (ux, ym, Z_USB), (ux, ya_u, Z_USB), (ux, ya_u, Z_FLACH),
                   (xe_u, ya_u, Z_FLACH), (xe_u, ya_u, Z_DICK), (xe_u, yk_u, Z_DICK), (xa + 2.2, yk_u, Z_DICK)]],
                 [(xa + 2.2, hinter, 10), (kx, hinter, 10), (kx, ky - 5, 10), (kx, ky - 5, hoch),
                  (kx, pult_hinten, hoch), (ziel_x, pult_hinten, hoch), (ziel_x, pult_hinten, jz),
                  (ziel_x, py + jy1 - 4, jz)])
            wege.append({"name": "19-V-Netzteil -> Jetson", "farbe": "netz19", "d": 4.5, "oben": False, "punkte": [
                (kx, ky + 5, -150), (kx, ky + 5, hoch + 6), (kx, pult_hinten + 6, hoch + 6),
                (px + jx1 - 20, pult_hinten + 6, hoch + 6), (px + jx1 - 20, pult_hinten + 6, jz),
                (px + jx1 - 20, py + jy1 - 4, jz)]})
        # Zuleitung zu den Sendern: Wago -> Kanal B -> Hülsenschlitz -> in den Pfosten.
        # Unten liegt der Pfosten lokal links, oben (gespiegelte Platte) lokal rechts.
        sd = "rechts" if oben else "links"
        px, py = next((x, y) for x, y in M.pfosten_xy() if y == M.Y_B and x * (-1 if oben else 1) < 0)
        for ai, (farbe, bus) in enumerate((("rot", "5V"), ("schwarz", "GND"))):
            xz = px + (ai - 0.5) * 3
            dazu(v, f"Zuleitung Sender {farbe} ({wort})", farbe, 1.8, oben,
                 _abgang_varianten(_rest_punkt(oben, sd, bus, 1), _raus(bus), M.Y_B, Z_ZULEITUNG, xz, y_raus=py),
                 [(xz, py, P.PLATTE_DICKE + 3)])
        if not oben:
            # LED-Streifen auf den vorderen Pfosten: 5V, GND (Wago der Seite) und Daten (Pico) -> Kanal A ->
            # Schlitz vor dem Pfosten -> innen an der Hülse vorbei nach vorne -> unteres Ende des Streifens
            h = P.PFOSTEN + 2 * P.SPIEL + 2 * P.HUELSE_WAND
            for sd, s in (("links", -1), ("rechts", 1)):
                px, yvorn, z0, _ = M.led_lage(s)
                daten, draus = _pin_punkt(PICO_PINS.index(f"GP{P.GPIO_LED[sd]}") + 1)
                for ai, (farbe, ende, raus, zu, aus, vs) in enumerate((
                        ("rot", _rest_punkt(False, sd, "5V", 3 if sd == "links" else 1), 1, Z_LED, TIEF + 5, 3),
                        ("schwarz", _rest_punkt(False, sd, "GND", 4 if sd == "links" else 1), -1, Z_LED, TIEF + 5, 3),
                        ("gelb", daten, draus, Z_LED_DATEN, 8, 1.65))):
                    xl = px + s * (1 - ai) * 2.0
                    innen = px - s * (h / 2 + 1.5 + ai * SPUR)         # innen neben der Hülse
                    vorne = M.Y_A - h / 2 - 2 - ai * 2.4
                    yq = M.Y_A + h / 2 + 4.6 + ai * SPUR                # zwischen Hülse und Kanalwand
                    xf = px + (ai - 1) * 2.0
                    dazu(v, f"Ader {farbe} LED {sd}", farbe, 1.6, False,
                         _abgang_varianten(ende, raus, M.Y_A, zu, xl, aus, yq, vs),
                         [(xl, yq, 5), (innen, yq, 5), (innen, vorne, 5), (xf, vorne, 5),
                          (xf, yvorn - P.LED_STREIFEN[1] - 1, z0 - T + 2)])
        # Sensoradern
        art = "Sender" if oben else "Empfänger"
        ziele = _belegung(oben)[0]
        for ebene, (y, xs) in zip("AB", M.EBENEN):
            for x in sorted(xs):
                nr = sensor_nr(xs, x, oben)
                adern = []
                for ai, farbe in enumerate(["rot", "schwarz"] if oben else ["rot", "schwarz", "gelb"]):
                    if farbe == "gelb":
                        ende, raus = _pin_punkt(pins[(ebene, x)]["pin"])
                    else:
                        ende, raus = ziele[(ebene, x, farbe)], _raus("5V" if farbe == "rot" else "GND")
                    adern.append((raus != -M.richtung(y), ai, farbe, ende, raus))
                for _, ai, farbe, ende, raus in sorted(adern):      # erst die direkten, dann die über die Reihe
                    dazu(v, f"Ader {farbe} {art} {ebene}{nr}", farbe, 1.4, oben,
                         _sensor_varianten(x, y, ai, ende, raus, farbe == "gelb"))
        ENGSTELLEN.update(v.eng)
    return wege


FARBE_3D = {"rot": "kabel_rot", "schwarz": "kabel", "gelb": "kabel_gelb", "usb": "usb", "netz": "kabel",
            "netz19": "kabel"}


def adern():
    teile = []
    zuleitung = {}
    for w in adern_wege():
        punkte = [welt(p, w["oben"]) for p in w["punkte"]]
        if w["name"].startswith("Zuleitung"):
            zuleitung.setdefault(w["farbe"], {})[w["oben"]] = punkte
            continue
        teile.append(_strang(punkte, w["d"], w["name"], FARBE_3D[w["farbe"]]))
    # Zuleitung unten + senkrecht im Pfosten + oben als eine Ader
    for farbe, teil_wege in zuleitung.items():
        weg = teil_wege[False] + list(reversed(teil_wege[True]))
        teile.append(_strang(weg, 1.8, f"Zuleitung Sender {farbe} (im Pfosten)", FARBE_3D[farbe]))
    return teile


# ---------------------------------------------------------------------------
# Bestücktes Nest
# ---------------------------------------------------------------------------
def nest_teile(oben):
    wort = "oben" if oben else "unten"
    L = M.nest_layout()
    teile = [teil(M.Pos(*welt((0, 0, P.PLATTE_DICKE), oben)) * (M.Rot(0, 180, 0) * M.elektronik_nest() if oben
                                                                 else M.elektronik_nest()),
                  f"Elektronik-Nest {wort} (Druckteil)", "druck")]
    z0 = P.PLATTE_DICKE + P.NEST_BODEN
    s = P.SPIEL

    def box(x0, x1, y0, y1, za, zb, name, farbe):
        a, b = welt((x0, y0, za), oben), welt((x1, y1, zb), oben)
        teile.append(teil(quader(min(a[0], b[0]), max(a[0], b[0]), y0, y1, min(a[2], b[2]), max(a[2], b[2])),
                          name, farbe))

    if not oben:
        bx0, bx1, by0, by1 = L["board"]
        box(bx0 + s, bx1 - s, by0 + s, by1 - s, z0, z0 + 1.6, "Schraubklemmen-Board", "platine")
        box(bx0 + s, bx1 - s, by0 + s, by0 + 8, z0 + 1.6, z0 + P.PICO_BOARD[2], "Schraubklemmen-Board Klemmen", "usb")
        box(bx0 + s, bx1 - s, by1 - 8, by1 - s, z0 + 1.6, z0 + P.PICO_BOARD[2], "Schraubklemmen-Board Klemmen", "usb")
        pl, pb, ph = P.PICO
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        box(cx - pl / 2, cx + pl / 2, cy - pb / 2, cy + pb / 2, z0 + 6, z0 + 6 + ph, "Raspberry Pi Pico 2 H", "pico")
        # DC-Kupplung links neben dem Nest, Buchse nach hinten (Netzteilstecker kommt über Kanal B
        # vom Austritt), grüne Klemme nach vorne -> 2 kurze Drähte zu den Wagos links
        dl, dd = P.DC_KUPPLUNG
        kx1 = L["aussen"][0] - 3
        ym = L["ym"]
        box(kx1 - dd, kx1, ym - dl / 2, ym + dl / 2, P.PLATTE_DICKE, P.PLATTE_DICKE + dd, "DC-Kupplung 5 V", "usb")
    bedarf = wago_bedarf()["oben" if oben else "unten"]
    wb, _, wh = P.WAGO
    for (sd, bus), (x0, x1, y0, y1) in L["wago"].items():
        for i in range(bedarf[(sd, bus)]):
            box(x0 + s + i * wb, x0 + s + (i + 1) * wb - 0.6, y0 + s, y1 - s, z0, z0 + wh,
                f"Wago {bus} {sd} {wort}", "wago")
    return teile


def elektronik():
    return nest_teile(False) + nest_teile(True) + adern()


# ---------------------------------------------------------------------------
# Kabellängen-Prüfung
# ---------------------------------------------------------------------------
RESERVE = 30                                 # Abisolieren (22 mm, doppelt gelegt) und Bögen


def sensor_laengen():
    """{Name: Länge} aller Sensoradern, entlang des verlegten Wegs."""
    return {w["name"]: sum(math.dist(a, b) for a, b in zip(w["punkte"], w["punkte"][1:]))
            for w in adern_wege() if w["name"].startswith("Ader") and (" Empfänger " in w["name"]
                                                                       or " Sender " in w["name"])}


def kabellaenge_max():
    return max(sensor_laengen().values())


def zu_kurz():
    """Sensoradern, für die das Sensorkabel samt Reserve nicht reicht, längste zuerst."""
    return sorted(((n, l) for n, l in sensor_laengen().items() if l + RESERVE > P.SENSORKABEL),
                  key=lambda x: -x[1])


def _laengen_text():
    kurz = zu_kurz()
    if not kurz:
        return f"reichen ohne Verlängerung (längster Weg ca. {kabellaenge_max() / 10:.0f} cm)"
    namen = ", ".join(f"{n.replace('Ader ', '')} ({l / 10:.0f} cm)" for n, l in kurz)
    return (f"reichen bis auf {len(kurz)} Adern; diese brauchen eine Verlängerung "
            f"(Wago 221-412 + Litze): {namen}")


# ---------------------------------------------------------------------------
# Verkabelungsplan (SVG), Anleitung (Markdown), Pinliste (JSON)
# ---------------------------------------------------------------------------
def _wago_text(platte, bus):
    b = wago_bedarf()[platte]
    return f"{b[('links', bus)]}× links + {b[('rechts', bus)]}× rechts"


def verkabelung_svg():
    """Draufsicht auf untere und obere Sensorplatte (Kind steht unten), maßstäblich.
    Halter, Kanäle, Nest, Pico und Wagos an ihren echten Orten; Adern auf denselben Wegen
    wie im 3D-Modell. Die obere Platte ist so gezeichnet, wie sie über der unteren liegt."""
    sk, rand, legende = 2.4, 30, 360
    x0, x1 = M.LEISTE_X0 - 6, M.LEISTE_X1 + 6
    y0, y1 = M.Y_A - 22, M.Y_B + 22
    pw, ph = (x1 - x0) * sk, (y1 - y0) * sk
    breite = rand * 2 + pw + legende
    kopf = 60
    hoehe = kopf + 2 * (ph + 70) + 40
    hex_ = {"rot": "#d62828", "schwarz": "#222", "gelb": "#e0a800", "usb": "#5a5a8a", "netz": "#777",
            "netz19": "#444"}
    L = M.nest_layout()
    pins = pin_belegung()
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{breite:.0f}" height="{hoehe:.0f}" '
         f'font-family="Segoe UI, Arial, sans-serif" font-size="12">',
         '<rect width="100%" height="100%" fill="#fff"/>',
         '<text x="20" y="30" font-size="20" font-weight="bold">Verkabelung – Draufsicht</text>',
         '<text x="20" y="50" fill="#555">Maßstäblich. Das Kind steht unten (Ebene A vorne). '
         'Gleiche Wege wie im 3D-Modell.</text>']

    def sx(x, spiegel):
        return rand + ((-x if spiegel else x) - x0) * sk

    def sy(y, oy):
        return oy + (y1 - y) * sk

    def rect(xa, ya, xb, yb, oy, spiegel, fill, stroke="#666"):
        a, b = sorted((sx(xa, spiegel), sx(xb, spiegel)))
        o.append(f'<rect x="{a:.1f}" y="{sy(yb, oy):.1f}" width="{b - a:.1f}" height="{(yb - ya) * sk:.1f}" '
                 f'fill="{fill}" stroke="{stroke}"/>')

    def text(x, y, oy, spiegel, t, size=11, fill="#000", anchor="middle", weight="normal", drehen=0):
        tx, ty = sx(x, spiegel), sy(y, oy)
        dreh = f' transform="rotate({drehen} {tx:.1f} {ty:.1f})"' if drehen else ""
        o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}"{dreh}>{t}</text>')

    def linie(punkte, oy, spiegel, farbe, dicke):
        pts = " ".join(f"{sx(x, spiegel):.1f},{sy(y, oy):.1f}" for x, y, _ in punkte
                       if y <= y1 + 10 and x0 - 40 <= x <= x1 + 40)
        o.append(f'<polyline points="{pts}" fill="none" stroke="{hex_[farbe]}" stroke-width="{dicke}" '
                 f'stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>')

    for nr, oben in enumerate((False, True)):
        oy = kopf + 30 + nr * (ph + 70)
        sp = oben                     # obere Platte ist lokal gespiegelt -> in Weltlage zeichnen
        titel = ("OBEN – Sender (Lage wie über der unteren Platte)" if oben
                 else "UNTEN – Empfänger, Pico und Wagos")
        o.append(f'<text x="{rand}" y="{oy - 10}" font-size="15" font-weight="bold">{titel}</text>')
        rect(M.LEISTE_X0, y0 + 4, M.LEISTE_X1, y1 - 4, oy, False, "#fafafa", "#bbb")
        text(M.LEISTE_X0 + 2, y0 + 6, oy, False, "vorne (Kind)", 10, "#888", "start")
        for y, xs in M.EBENEN:
            i0, i1 = M.kanal_y(y)
            rect(M.LEISTE_X0, i0, M.LEISTE_X1, i1, oy, sp, "#e9eef7", "#9ab")
            ebene = "A" if y == M.Y_A else "B"
            ga, gb, _, _ = M.gehaeuse_y(y, M.richtung(y))
            for x in xs:
                rect(x - M.TURM_X / 2, ga - 2, x + M.TURM_X / 2, gb + 2, oy, sp, "#2b2b2b", "#000")
                text(x, (M.Y_A - 14) if ebene == "A" else (M.Y_B + 16), oy, sp,
                     f"{ebene}{sensor_nr(xs, x, oben)}", 11, weight="bold")
        h = P.PFOSTEN + 2 * P.SPIEL + 2 * P.HUELSE_WAND
        for px_, py_ in M.pfosten_xy():
            rect(px_ - h / 2, py_ - h / 2, px_ + h / 2, py_ + h / 2, oy, False, "#bbb", "#777")
        ax0, ax1, ay0, ay1 = L["aussen"]
        rect(ax0, ay0, ax1, ay1, oy, sp, "#dfe9ff", "#7a9")
        bedarf = wago_bedarf()["oben" if oben else "unten"]
        wb = P.WAGO[0]
        for (sd, bus), (wx0, wx1, wy0, wy1) in L["wago"].items():
            k = bedarf[(sd, bus)]
            for i in range(k):
                rect(wx0 + i * wb + 0.3, wy0 + 0.3, wx0 + (i + 1) * wb - 0.3, wy1 - 0.3, oy, sp, "#ffb45c", "#b06a00")
            text(wx0 + k * wb / 2, (wy0 + wy1) / 2 - 2, oy, sp, f"Wago {bus}", 10, "#7a4200", weight="bold")
        if not oben:
            bx0, bx1, by0, by1 = L["board"]
            rect(bx0, by0, bx1, by1, oy, sp, "#cdeccf", "#2a7a3a")
            text((bx0 + bx1) / 2, (by0 + by1) / 2 - 2, oy, sp, "Pico 2 H", 12, "#1d5a2a", weight="bold")
            text(bx0 + 2, (by0 + by1) / 2 - 2, oy, sp, "USB", 9, "#335", "start")
            for pn in pins:
                x, y, _ = pico_pin_ort(pn["pin"])
                o.append(f'<circle cx="{sx(x, sp):.1f}" cy="{sy(y, oy):.1f}" r="3" fill="#e0a800" stroke="#7a5a00"/>')
                if pn["pin"] <= 20:
                    text(x, y - 3, oy, sp, f"GP{pn['gpio']}", 8, "#5a4300", "end", drehen=-90)
                else:
                    text(x, y + 3, oy, sp, f"GP{pn['gpio']}", 8, "#5a4300", "start", drehen=-90)
        for w in adern_wege():
            if w["oben"] == oben:
                linie(w["punkte"], oy, sp, w["farbe"], 1.5 if w["d"] < 3 else 3.5)
        if oben:
            text(-191, M.Y_B + 16, oy, False, "↓ 2 Adern im Pfosten", 9, "#a00")
        else:
            text(M.austritt_x() + 8, y1 - 2, oy, False, "↑ USB + 5 V raus", 10, "#335", "start")
            text(M.LEISTE_X0 + 20, M.Y_A - 18, oy, False, "LED links ↑", 9, "#a00", "start")
            text(M.LEISTE_X1 - 20, M.Y_A - 18, oy, False, "↑ LED rechts", 9, "#a00", "end")
            text(-191, M.Y_B + 16, oy, False, "↑ 2 Adern im Pfosten", 9, "#a00")

    lx = rand * 2 + pw
    ly = kopf + 40
    o.append(f'<text x="{lx}" y="{ly}" font-size="14" font-weight="bold">Adern</text>')
    for i, (f, t) in enumerate((("rot", "rot = 5 V → Wago 5V"), ("schwarz", "schwarz = GND → Wago GND"),
                                ("gelb", "gelb = Signal → Pico (nur Empfänger)"),
                                ("usb", "USB-Kabel → Jetson (über Kabelkanal)"), ("netz", "5-V-Netzteil → Wago links"))):
        y = ly + 22 + i * 18
        o.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 26}" y2="{y - 4}" stroke="{hex_[f]}" stroke-width="3"/>')
        o.append(f'<text x="{lx + 34}" y="{y}">{t}</text>')
    ly += 140
    o.append(f'<text x="{lx}" y="{ly}" font-size="14" font-weight="bold">Pico-Pins (Empfänger)</text>')
    nummer = {"A": 0, "B": 0}
    for i, pn in enumerate(pins):
        nummer[pn["ebene"]] += 1
        o.append(f'<text x="{lx}" y="{ly + 22 + i * 16}">{pn["ebene"]}{nummer[pn["ebene"]]}  '
                 f'({pn["x_mm"]:+d} mm)  →  GP{pn["gpio"]}  (Pin {pn["pin"]})</text>')
    ly += 40 + len(pins) * 16
    for t in ("Sensoren links → linke Wagos, rechts → rechte;",
              "linke und rechte Wago-Reihe sind gebrückt.",
              f"Pico-GND (Pin {PICO_PINS.index('GND') + 1}) → Wago GND links.",
              "Nie ein gelbes Signal an 5 V!"):
        o.append(f'<text x="{lx}" y="{ly}" fill="{"#b00000" if "Nie" in t else "#000"}">{t}</text>')
        ly += 17
    o.append("</svg>")
    return "\n".join(o)


def verkabelung_md():
    pins = pin_belegung()
    wb = wago_bedarf()
    zeilen = "\n".join(f"| {p['nr']} | {p['ebene']} | {p['seite']} | {p['x_mm']:+d} mm | GP{p['gpio']} | {p['pin']} |"
                       for p in pins)
    return f"""# Verkabelung – Schlag-Messgerät

*Automatisch erzeugt von `build.py` – nicht von Hand ändern.* Plan als Bild: `ausgabe/Verkabelung.svg`

## Wo was sitzt
- **Elektronik-Nest unten** (Druckteil, mittig zwischen A und B): Pico 2 H auf Schraubklemmen-Board,
  links und rechts davon je eine Reihe Wago 5V und GND (unten: 5V {_wago_text('unten', '5V')}, GND {_wago_text('unten', 'GND')}).
  Sensoren links gehen in die linken Wagos, rechts in die rechten; beide Seiten sind gebrückt.
  Liegt unter dem Messfenster, keine Faust kommt hin.
- **Nest oben** (gleiches Druckteil): nur Wagos für die Sender (5V {_wago_text('oben', '5V')}, GND {_wago_text('oben', 'GND')}).
- **Kabelkanäle** direkt neben den Sensorhaltern, mit Einführschlitz je Halter und Rastlippe.
  Sensorkabel ({P.SENSORKABEL // 10} cm) {_laengen_text()}.
- **Kabelführung**: rechtwinklig und in festen Höhen, keine Ader berührt eine andere. Wago-Einlässe zeigen nach
  außen (5V-Reihe nach hinten, GND-Reihe nach vorne). Adern zur abgewandten Reihe laufen über die Wagos hinweg
  und kommen von der anderen Seite. USB und Netzteil liegen flach hinter dem Nest.
- **Zuleitung zu den Sendern**: 2 Adern 0,5 mm² durch den hohlen hinteren linken Alu-Pfosten.
- **Raus** gehen nur USB (Pico → Jetson) und das 5-V-Netzteil, hinten links über die Kante.
- **Deckel** (gedruckt, 2 Hälften je Platte, per Schwalbenschwanz verklebt) liegt auf 4 Säulen über dem Mittelfeld
  und versteckt Nest, Wagos und Adern; Schürzen vorne und hinten liegen auf den Kabelkanälen auf (blickdicht,
  stützen den Deckel über die ganze Länge); 4 Schrauben {P.SCHRAUBE_SENSOR[0]}×{P.SCHRAUBE_SENSOR[1]} je Deckel – zum Basteln einfach abschrauben.

## Adern am Sensor
| Teil | rot | schwarz | gelb/weiß |
|---|---|---|---|
| Empfänger (unten, 3 Adern) | Wago 5V unten | Wago GND unten | Pico laut Tabelle |
| Sender (oben, 2 Adern) | Wago 5V oben | Wago GND oben | – |

So kommt eine Sensorader in die Wago (oder Schraubklemme):
1. Den kleinen Stiftstecker am Ende mit dem Seitenschneider abknipsen.
2. **22 mm** abisolieren, die Litze fest verdrillen und **in der Mitte umknicken** (11 mm, doppelt dick) –
   die Sensoradern sind sehr dünn, doppelt gelegt klemmt die Wago sicher.
3. Hebel hoch, Ader bis zum Anschlag einstecken, Hebel runter, kurz daran ziehen.

Falls doch einmal eine Ader zu kurz ist: mit einer weiteren Wago und einem Stück Litze verlängern.

## LED-Streifen
- Je ein WS2812B-Streifen ({led_anzahl_text()}) links und rechts am Fensterrand.
- Sitzen auf der **Vorderseite der vorderen Alu-Pfosten** (Streifen 10 mm = Rohr 10 mm), Klebeband hinten
  vom Streifen abziehen und aufkleben, **Pfeile nach oben** (Daten kommen von unten).
- 1-m-Streifen kaufen und teilen: das Stück **mit** Stecker nach links, das zweite Stück bekommt einen
  **lötfreien Klemmverbinder** (3-polig, 10 mm) mit Kabel.
- Je Seite 3 Adern: rot → Wago 5V, schwarz → Wago GND, Daten → Pico (Tabelle unten).
  Weg: Kanal A zur Seite, durch den Schlitz vor dem Pfosten, innen an der Hülse vorbei zum unteren Streifenende.
- Strom: max. {led_strom_a():.1f} A bei voller Helligkeit; die Firmware begrenzt auf {P.LED_HELLIGKEIT:.0%}
  → ca. {led_strom_a() * P.LED_HELLIGKEIT:.1f} A. Netzteil {P.NETZTEIL_A:.0f} A reicht.
- **330-Ω-Widerstand in jede Datenleitung** (Pflicht): ein Bein in die Pico-Klemme (GP-Pin), das andere mit der
  gelben LED-Datenader in eine Wago 221-412. Schützt den Pico, wenn die LEDs noch keinen Strom haben.
- **Kondensator 1000 µF / 10 V** an den Netzteil-Eingang: langes Bein (+) in Wago 5V rechts, kurzes Bein (−, Streifen
  auf dem Gehäuse) in Wago GND rechts. **Polung beachten** – falsch herum kann er platzen.
- Flackern die LEDs trotzdem: Pegelwandler (3,3 V → 5 V, z. B. 74AHCT125) in die Datenleitung.

## Pinbelegung (Empfänger-Signal)
| Nr | Ebene | Seite | Position | Pico | Pin |
|---|---|---|---|---|---|
{zeilen}
| – | – | – | – | GND | {PICO_PINS.index('GND') + 1} → Wago GND unten |
| – | LED | links | – | GP{P.GPIO_LED['links']} | {PICO_PINS.index(f"GP{P.GPIO_LED['links']}") + 1} → Daten LED-Streifen links |
| – | LED | rechts | – | GP{P.GPIO_LED['rechts']} | {PICO_PINS.index(f"GP{P.GPIO_LED['rechts']}") + 1} → Daten LED-Streifen rechts |

## Reihenfolge
1. Sensoren in die Halter legen, je eine Schraube {P.SCHRAUBE_SENSOR[0]}×{P.SCHRAUBE_SENSOR[1]} durchs Loch.
2. Adern durch den Einführschlitz in den Kanal drücken, bis die Rastlippe sie hält; zum Nest führen.
3. Jede gelbe Ader mit ihrer Nummer beschriften (Klebeband), dann in die Klemme laut Tabelle.
4. Rot/schwarz in die Wago-Reihen; die Wagos einer Reihe mit einem kurzen Drahtstück verbinden.
5. 2 Adern (rot, schwarz) unten durch den Hülsen-Schlitz in den hinteren linken Pfosten, oben wieder raus,
   oben in Wago 5V/GND. (Am Rohr unten und oben je eine 6-mm-Kerbe aussägen.)
6. Pico-GND an Wago GND unten. **Pico-VBUS / VSYS bleiben frei** – der Pico bekommt Strom nur über USB. DC-Kupplung (Schraubklemmen + / −) liegt links neben dem Nest (Buchse nach hinten zum Kabelaustritt), mit 2 kurzen Drähten an Wago 5V/GND links
   links unten; Polung vor dem ersten Einstecken mit dem Multimeter prüfen. USB-Kabel an den Pico.
7. Erst testen (Strahlen unterbrechen, Anzeige im Terminal), dann den Käfig in die Kiste schieben.
"""


def led_strom_a():
    return 2 * M.led_anzahl() * P.LED_STROM_MA / 1000


def led_anzahl_text():
    return f"{M.led_anzahl()} LEDs je Seite, {P.LED_PRO_M}/m"


def pins_json():
    return json.dumps({"gpio_led": P.GPIO_LED, "leds_je_seite": M.led_anzahl(), "led_helligkeit": P.LED_HELLIGKEIT,
                       "ebenenabstand_mm": P.EBENENABSTAND_AB, "sensoren": pin_belegung()},
                      indent=2, ensure_ascii=False)


if __name__ == "__main__":
    print(verkabelung_md())
    print("Wago:", wago_bedarf(), " längster Adernweg:", round(kabellaenge_max()), "mm")
