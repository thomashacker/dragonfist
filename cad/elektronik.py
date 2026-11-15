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


def _wago_punkt(sd, bus, i, n, z_extra=0):
    """i-te von n Adern in der Wago-Reihe (seite, bus), lokal."""
    x0, x1, y0, y1 = M.nest_layout()["wago"][(sd, bus)]
    return (x0 + 3 + (x1 - x0 - 6) * (i + 0.5) / n, (y0 + y1) / 2,
            P.PLATTE_DICKE + P.NEST_BODEN + P.WAGO[2] + z_extra)


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


def _ader_weg(x, y, ai, lane, ziel):
    """Weg einer Ader (lokal): Halter -> Einführschlitz -> Kanal -> Nest -> Ziel."""
    r = M.richtung(y)
    _, _, kabel, _ = M.gehaeuse_y(y, r)
    i0, i1 = M.kanal_y(y)
    nx0, nx1, ny0, ny1 = M.nest_layout()["aussen"]
    dx = (ai - 1) * 1.6
    raus = kabel + r * (P.SPIEL + P.TURM_WAND)
    cy = (i0 + 2 + ai * 3.2) if r > 0 else (i1 - 2 - ai * 3.2)
    cz = P.PLATTE_DICKE + 1.5 + (lane % 4) * 2.4
    xe = min(max(x + dx, nx0 + 18), nx1 - 18)
    ny = ny0 if r > 0 else ny1
    # aus dem Kanal heraus schräg über den Nestrand zur Klemme (so liegt eine echte Ader)
    return [(x + dx, raus, 3), (x + dx, cy, cz), (xe, cy, cz), (ziel[0], ny, ziel[2]), ziel]


def _belegung(oben):
    """Welche Ader in welche Wago-Reihe, mit laufender Nummer je Reihe: {(ebene, x, farbe): ziel}."""
    leiter = M.nest_leiter()["oben" if oben else "unten"]
    zaehler = {key: 0 for key in leiter}
    ziele = {}
    for ebene, (y, xs) in zip("AB", M.EBENEN):
        for x in sorted(xs):
            for farbe, bus in (("rot", "5V"), ("schwarz", "GND")):
                key = (M.seite(x), bus)
                ziele[(ebene, x, farbe)] = _wago_punkt(*key, zaehler[key], leiter[key])
                zaehler[key] += 1
    return ziele, zaehler, leiter


def _rest_punkt(oben, sd, bus, nr):
    """Freier Platz nr in einer Wago-Reihe nach den Sensor-Adern (Brücke, Zuleitung, Netzteil, GND)."""
    _, zaehler, leiter = _belegung(oben)
    return _wago_punkt(sd, bus, zaehler[(sd, bus)] + nr, leiter[(sd, bus)])


def adern_wege():
    """Alle Leitungen als Wege in Platten-Koordinaten:
    [{"name", "farbe", "d", "oben", "punkte"}]. Daraus entstehen 3D-Modell und 2D-Plan."""
    wege = []
    pins = {(p["ebene"], p["x_mm"]): p for p in pin_belegung()}
    for oben in (False, True):
        art = "Sender" if oben else "Empfänger"
        farben = ["rot", "schwarz"] if oben else ["rot", "schwarz", "gelb"]
        ziele, _, _ = _belegung(oben)
        for ebene, (y, xs) in zip("AB", M.EBENEN):
            for lane, x in enumerate(sorted(xs)):
                for ai, farbe in enumerate(farben):
                    ziel = pico_pin_ort(pins[(ebene, x)]["pin"]) if farbe == "gelb" else ziele[(ebene, x, farbe)]
                    nr = sensor_nr(xs, x, oben)
                    wege.append({"name": f"Ader {farbe} {art} {ebene}{nr}", "farbe": farbe, "d": 1.4,
                                 "oben": oben, "punkte": _ader_weg(x, y, ai, lane, ziel)})
        # Brücken zwischen linker und rechter Wago-Reihe: neben dem Board vorbei (5V hinten, GND vorne),
        # knapp über den Nestwänden – nicht über den Pico, sonst wird es unter dem Deckel zu eng
        _, _, by0, by1 = M.nest_layout()["board"]
        hz = P.PLATTE_DICKE + P.NEST_BODEN + P.NEST_HOEHE + 2
        for farbe, bus, yb in (("rot", "5V", by1 + 4), ("schwarz", "GND", by0 - 4)):
            a, b = _rest_punkt(oben, "links", bus, 0), _rest_punkt(oben, "rechts", bus, 0)
            wege.append({"name": f"Ader {farbe} Brücke {bus} {'oben' if oben else 'unten'}", "farbe": farbe,
                         "d": 1.8, "oben": oben,
                         "punkte": [a, (a[0], a[1], hz), (a[0], yb, hz), (b[0], yb, hz), (b[0], b[1], hz), b]})
        # Zuleitung zu den Sendern: Wago -> Kanal B -> Hülsenschlitz -> in den Pfosten
        for ai, farbe in enumerate(("rot", "schwarz")):
            wege.append({"name": f"Zuleitung Sender {farbe} ({'oben' if oben else 'unten'})", "farbe": farbe,
                         "d": 1.8, "oben": oben, "punkte": _pfosten_weg(farbe, ai, oben)})
    # Pico-GND an die linke GND-Reihe unten
    gnd = pico_pin_ort(PICO_PINS.index("GND") + 1)
    ziel = _rest_punkt(False, "links", "GND", 3)
    wege.append({"name": "Ader schwarz Pico-GND", "farbe": "schwarz", "d": 1.4, "oben": False,
                 "punkte": [gnd, (gnd[0], gnd[1], gnd[2] + 5), (ziel[0], ziel[1], gnd[2] + 5), ziel]})
    # LED-Streifen auf den vorderen Pfosten: 5V, GND (Wago der Seite) und Daten (Pico) -> Kanal A ->
    # Schlitz vor dem Pfosten -> innen an der Hülse vorbei nach vorne -> unteres Ende des Streifens
    ka0, _ = M.kanal_y(M.Y_A)
    ny0 = M.nest_layout()["aussen"][2]
    h = P.PFOSTEN + 2 * P.SPIEL + 2 * P.HUELSE_WAND
    for sd, s in (("links", -1), ("rechts", 1)):
        px, yv, z0, _ = M.led_lage(s)
        for ai, (farbe, start) in enumerate((
                ("rot", _rest_punkt(False, sd, "5V", 3 if sd == "links" else 1)),
                ("schwarz", _rest_punkt(False, sd, "GND", 4 if sd == "links" else 1)),
                ("gelb", pico_pin_ort(PICO_PINS.index(f"GP{P.GPIO_LED[sd]}") + 1)))):
            d = (ai - 1) * 2.0
            cy, cz = ka0 + 3 + ai * 3, P.PLATTE_DICKE + P.KANAL_INNEN[1] - 2
            innen = px - s * (h / 2 + 1.5 + ai * 1.6)            # innen neben der Hülse
            vorne = M.Y_A - h / 2 - 2
            wege.append({"name": f"Ader {farbe} LED {sd}", "farbe": farbe, "d": 1.6, "oben": False, "punkte": [
                start, (start[0], ny0, start[2]), (start[0] + d, cy, cz), (px + d, cy, cz),
                (innen, M.Y_A + h / 2 + 2, 5), (innen, vorne, 5), (px + d, vorne, 5),
                (px + d, yv - P.LED_STREIFEN[1] - 1, z0 - T + 2)]})

    # USB und Netzteil: Kanal B -> Austritt hinten links -> um die Brettkante in den Kabelkanal außen.
    # USB läuft darin nach oben ins Pult (Jetson), 5 V kommt von unten (Netzteil am Boden).
    # Dazu das 19-V-Kabel des Jetson: von unten durch den Kanal hoch und hinten ins Pult.
    import pult as PU                                          # spät: pult baut auf modell auf
    L = M.nest_layout()
    bx0, _, by0, by1 = L["board"]
    i0, i1 = M.kanal_y(M.Y_B)
    ny1 = L["aussen"][3]
    xa, cy = M.austritt_x(), (i0 + i1) / 2
    kx, ky = M.kabelkanal_mitte()
    hinter = M.TIEFE + 12
    oben = M.AUSSEN_H - T + 6                                   # lokal: knapp über dem oberen Brett
    px, py, _ = PU.lage_auf_kiste()
    jx0, jx1, jy0, jy1, jz0, jz1 = PU.jetson_lage()
    pult_hinten = py + P.PULT_TIEFE + 8
    jz = M.AUSSEN_H - T + (jz0 + jz1) / 2                       # Höhe der Jetson-Anschlüsse (lokal)
    for name, farbe, start, dx, dy, nach_oben, ziel_x in (
            ("USB-Kabel Pico -> Jetson", "usb", (bx0 - 2, (by0 + by1) / 2, P.PLATTE_DICKE + 8), -2.2, -5, True,
             px + jx0 + 20),
            ("5-V-Netzteil -> Wago", "netz", _rest_punkt(False, "links", "5V", 2), 2.2, 0, False, None)):
        weg = [start, (start[0], ny1, start[2]), (start[0], cy, 10), (xa + dx, cy, 10), (xa + dx, hinter, 10),
               (kx, hinter, 10), (kx, ky + dy, 10)]
        if nach_oben:
            weg += [(kx, ky + dy, oben), (kx, pult_hinten, oben), (ziel_x, pult_hinten, oben),
                    (ziel_x, pult_hinten, jz), (ziel_x, py + jy1 - 4, jz)]
        else:
            weg += [(kx, ky + dy, -150)]
        wege.append({"name": name, "farbe": farbe, "d": 4, "oben": False, "punkte": weg})
    wege.append({"name": "19-V-Netzteil -> Jetson", "farbe": "netz19", "d": 4.5, "oben": False, "punkte": [
        (kx, ky + 5, -150), (kx, ky + 5, oben + 6), (kx, pult_hinten + 6, oben + 6), (px + jx1 - 20, pult_hinten + 6,
                                                                                         oben + 6),
        (px + jx1 - 20, pult_hinten + 6, jz), (px + jx1 - 20, py + jy1 - 4, jz)]})
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


def _pfosten_weg(farbe, ai, oben):
    """Von der Wago-Reihe durch Kanal B zum hinteren Pfosten links (lokal).
    Unten liegt der Pfosten lokal links, oben (gespiegelte Platte) lokal rechts."""
    sd = "rechts" if oben else "links"
    start = _rest_punkt(oben, sd, "5V" if farbe == "rot" else "GND", 1)
    px, py = next((x, y) for x, y in M.pfosten_xy() if y == M.Y_B and x * (-1 if oben else 1) < 0)
    i0, i1 = M.kanal_y(M.Y_B)
    _, _, _, ny1 = M.nest_layout()["aussen"]
    cy, cz = i0 + 3 + ai * 3, P.PLATTE_DICKE + 4
    d = P.PLATTE_DICKE + 3
    return [start, (start[0], ny1, start[2]), (start[0], cy, cz), (px + (ai - 0.5) * 3, cy, cz),
            (px + (ai - 0.5) * 3, py, d)]


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
def kabellaenge_max():
    """Längster Adernweg Sensor -> Ziel (lokal, Polylinie)."""
    pins = {(p["ebene"], p["x_mm"]): p for p in pin_belegung()}
    laengen = []
    for oben in (False, True):
        ziele, _, _ = _belegung(oben)
        for ebene, (y, xs) in zip("AB", M.EBENEN):
            for lane, x in enumerate(sorted(xs)):
                ende = [ziele[(ebene, x, "rot")], ziele[(ebene, x, "schwarz")]]
                if not oben:
                    ende.append(pico_pin_ort(pins[(ebene, x)]["pin"]))
                for ai, ziel in enumerate(ende):
                    weg = _ader_weg(x, y, ai, lane, ziel)
                    laengen.append(sum(math.dist(a, b) for a, b in zip(weg, weg[1:])))
    return max(laengen)


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
  Sensorkabel ({P.SENSORKABEL // 10} cm) reichen ohne Verlängerung (längster Weg ca. {kabellaenge_max() / 10:.0f} cm).
- **Zuleitung zu den Sendern**: 2 Adern 0,5 mm² durch den hohlen hinteren linken Alu-Pfosten.
- **Raus** gehen nur USB (Pico → Jetson) und das 5-V-Netzteil, hinten links über die Kante.
- **Deckel** (gedruckt, 2 Hälften je Platte) liegt auf 4 Säulen über dem Mittelfeld und versteckt Nest, Wagos
  und Adern; 4 Schrauben {P.SCHRAUBE_SENSOR[0]}×{P.SCHRAUBE_SENSOR[1]} je Deckel – zum Basteln einfach abschrauben.

## Adern am Sensor
| Teil | rot | schwarz | gelb/weiß |
|---|---|---|---|
| Empfänger (unten, 3 Adern) | Wago 5V unten | Wago GND unten | Pico laut Tabelle |
| Sender (oben, 2 Adern) | Wago 5V oben | Wago GND oben | – |

**Keine Verlängerung nötig.** So kommt eine Sensorader in die Wago (oder Schraubklemme):
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
- **Kondensator 1000 µF / 10 V** an den Netzteil-Eingang: langes Bein (+) in Wago 5V links, kurzes Bein (−, Streifen
  auf dem Gehäuse) in Wago GND links. **Polung beachten** – falsch herum kann er platzen.
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
