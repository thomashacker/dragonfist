"""
Geometrie des Schlag-Messgeräts (build123d). Maße kommen aus parameter.py.
"""
import math

from build123d import (
    Align, Box, Color, Compound, Cylinder, Plane, Polygon, Pos, Rot, Sphere,
    Vector, extrude,
)

import parameter as P

# ---------------------------------------------------------------------------
# Abgeleitete Maße
# ---------------------------------------------------------------------------
T = P.BRETT_DICKE
W = P.FENSTER_BREITE
# Halterhöhe: liegendes Gehäuse + LED-Kuppe + Blendtunnel darüber
LEISTE_DICKE = P.SENSOR_HOEHE + P.SPIEL + P.LED_UEBERSTAND + P.TUNNEL_LAENGE
INNEN_H = P.FENSTER_HOEHE + 2 * LEISTE_DICKE
AUSSEN_H = INNEN_H + 2 * T
AUSSEN_W = W + 2 * T

Y_A = P.EBENE_A_VON_VORNE
Y_B = Y_A + P.EBENENABSTAND_AB
EBENEN = [(Y_A, P.STRAHLEN_A), (Y_B, P.STRAHLEN_B)]
TIEFE = max(P.RAHMEN_TIEFE, Y_B + P.STREIFEN_BREITE / 2)

LEISTE_X0 = -W / 2 + P.LEISTE_LUFT_SEITLICH
LEISTE_X1 = W / 2 - P.LEISTE_LUFT_SEITLICH

FARBEN = {
    "holz": Color(0.87, 0.72, 0.50),
    "holz_dunkel": Color(0.72, 0.55, 0.35),
    "druck": Color(0.20, 0.45, 0.85),
    "druck_c": Color(0.30, 0.70, 0.95),
    "sensor": Color(0.10, 0.10, 0.10),
    "strahl": Color(0.95, 0.15, 0.15),
    "schaum": Color(0.20, 0.85, 0.40),
    "trennung": Color(0.98, 0.80, 0.10),
    "alu": Color(0.80, 0.80, 0.82),
    "led": Color(0.95, 0.95, 1.00),
    "stahl": Color(0.25, 0.25, 0.28),
    "flansch": Color(0.15, 0.15, 0.15),
    "sand": Color(0.55, 0.45, 0.25),
    "dose": Color(0.90, 0.90, 0.88),
    "haut": Color(0.95, 0.75, 0.60),
    "boden": Color(0.55, 0.55, 0.58),
    "klebeband": Color(1.00, 0.55, 0.00),
    "kabel": Color(0.12, 0.12, 0.12),
    "kabel_rot": Color(0.85, 0.10, 0.10),
    "kabel_gelb": Color(0.95, 0.80, 0.10),
    "wago": Color(0.95, 0.55, 0.10),
    "platine": Color(0.10, 0.45, 0.25),
    "pico": Color(0.15, 0.60, 0.30),
    "usb": Color(0.25, 0.25, 0.30),
    "deckel": Color(0.30, 0.30, 0.34),
    "bildschirm": Color(0.10, 0.35, 0.75),
    "knopf": Color(0.95, 0.80, 0.10),
    "knopf_start": Color(0.10, 0.75, 0.25),
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def quader(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def zyl_z(x, y, z0, z1, d):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def zyl_x(x0, x1, y, z, d):
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, x1 - x0)


def zyl_y(x, y0, y1, z, d):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, y1 - y0)


def stab(p0, p1, d):
    v = Vector(*p1) - Vector(*p0)
    return Plane(origin=p0, z_dir=v) * Cylinder(
        d / 2, v.length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def teil(form, name, farbe):
    form.label = name
    form.color = FARBEN[farbe]
    return form


# ---------------------------------------------------------------------------
# Gedruckte Sensorplatte
#   Platten-Koordinaten: Brettseite z=0, Strahlseite z=LEISTE_DICKE (Strahl zeigt +Z),
#   Y wie im Rahmen. So ist es die UNTERE Platte; die obere ist um Y gedreht.
#   Aufbau: dünnes Gitter (Streifen unter A und B, Querrippen mit Schraubaugen)
#   und pro Sensor ein Halter: flache Tasche für das liegende Gehäuse (von der
#   Brettseite eingelegt), Dach mit Schraubloch, darüber Säule mit LED-Sitz und
#   Blendtunnel. (x, y) ist immer die LED-Mitte = Strahlposition.
# ---------------------------------------------------------------------------
TURM_X = P.SENSOR_BREITE + 2 * (P.SPIEL + P.TURM_WAND)
SAEULE = P.LED_DURCHMESSER + P.SPIEL + 2 * P.TURM_WAND
TASCHE_H = P.SENSOR_HOEHE + P.SPIEL


def richtung(y):
    """+1: Kabel zeigt nach hinten (+Y), -1: nach vorne."""
    return P.KABEL_RICHTUNG["A" if y == Y_A else "B"]


def gehaeuse_y(y, r):
    """Y-Bereich des Gehäuses (vorne, hinten) und Lage des Befestigungslochs."""
    stirn = y - r * P.LED_VON_STIRN
    kabel = y + r * (P.SENSOR_LAENGE - P.LED_VON_STIRN)
    loch = kabel - r * P.LOCH_VON_KABEL
    return min(stirn, kabel), max(stirn, kabel), kabel, loch


def _sensor_loch(x, y, r):
    s = P.SPIEL
    y0, y1, _, loch = gehaeuse_y(y, r)
    led_oben = TASCHE_H + P.LED_UEBERSTAND
    return (
        quader(x - P.SENSOR_BREITE / 2 - s, x + P.SENSOR_BREITE / 2 + s, y0 - s, y1 + s, -1, TASCHE_H)
        + zyl_z(x, y, TASCHE_H - 0.5, led_oben, P.LED_DURCHMESSER + s)
        + zyl_z(x, y, led_oben - 0.5, LEISTE_DICKE + 1, P.TUNNEL_DURCHMESSER)
        + zyl_z(x, loch, TASCHE_H - 0.5, TASCHE_H + P.TURM_WAND + 1, P.SENSOR_SCHRAUBE_D)
    )


def _kabelkerbe(x, y, r):
    kb, kh = P.KABELKERBE
    _, _, kabel, _ = gehaeuse_y(y, r)
    aussen = kabel + r * (P.SPIEL + P.TURM_WAND + 1)
    return quader(x - kb / 2, x + kb / 2, min(kabel, aussen), max(kabel, aussen), -1, kh)


def _turm(x, y, r):
    w = P.SPIEL + P.TURM_WAND
    y0, y1, _, _ = gehaeuse_y(y, r)
    sockel = quader(x - TURM_X / 2, x + TURM_X / 2, y0 - w, y1 + w, 0, TASCHE_H + P.TURM_WAND)
    return sockel + quader(x - SAEULE / 2, x + SAEULE / 2, y - SAEULE / 2, y + SAEULE / 2, 0, LEISTE_DICKE)


def leisten_stuecke():
    grenzen = [LEISTE_X0] + sorted(P.LEISTE_TEILUNGEN) + [LEISTE_X1]
    return list(zip(grenzen, grenzen[1:]))


def _rippe_frei(x):
    abstand = TURM_X / 2 + P.SCHRAUBAUGE_D / 2 + 2
    return all(abs(x - xt) >= abstand for _, xs in EBENEN for xt in xs)


def rippen_x():
    """Querrippen an beiden Enden jedes Stücks und in der Mitte, jeweils neben die Türmchen
    geschoben, damit die Kabel frei nach hinten laufen. An Trennfugen bleibt Platz für
    den Schwalbenschwanz."""
    def rand(x):
        aussen = x in (LEISTE_X0, LEISTE_X1)
        return P.SCHRAUBAUGE_D / 2 + 1 if aussen else P.SCHWALBE[0] + P.SCHRAUBAUGE_D / 2 + 3

    xs = []
    for a, b in leisten_stuecke():
        lo, hi = a + rand(a), b - rand(b)
        for start, richtung in ((lo, 1), ((a + b) / 2, 1), (hi, -1)):
            x = start
            while not _rippe_frei(x) and lo <= x <= hi:
                x += richtung
            if lo <= x <= hi:
                xs.append(x)
    return xs


def pfosten_xy():
    """Pfosten an den Enden der beiden Streifen, direkt an den Seitenbrettern."""
    h = P.PFOSTEN + 2 * P.SPIEL + 2 * P.HUELSE_WAND
    return [(s * (LEISTE_X1 - h / 2), y) for s in (-1, 1) for y in (Y_A, Y_B)]


def _huelse(x, y, loch=False):
    p = P.PFOSTEN + 2 * P.SPIEL
    h = p + 2 * P.HUELSE_WAND
    if loch:
        d = P.PLATTE_DICKE
        form = quader(x - p / 2, x + p / 2, y - p / 2, y + p / 2, d, d + P.HUELSE_HOEHE + 1)
        # Schlitz unten zur Plattenmitte hin: dort kommen die Adern aus dem hohlen Pfosten
        sb, sh = P.HUELSE_SCHLITZ
        s = 1 if y == Y_A else -1
        y0, y1 = sorted((y + s * (p / 2 - 0.5), y + s * (h / 2 + 0.5)))
        return form + quader(x - sb / 2, x + sb / 2, y0, y1, d, d + sh)
    return quader(x - h / 2, x + h / 2, y - h / 2, y + h / 2, 0, P.PLATTE_DICKE + P.HUELSE_HOEHE)


def pfosten_laenge():
    # sitzt unten und oben auf der Platte am Hülsengrund auf
    return INNEN_H - 2 * P.PLATTE_DICKE


# ---------------------------------------------------------------------------
# Kabelkanäle: je einer direkt neben den Haltern von A und B, zur Mitte hin
# ---------------------------------------------------------------------------
def kanal_y(y):
    """Innenraum (y0, y1) des Kanals an Ebene y."""
    r = richtung(y)
    _, _, kabel, _ = gehaeuse_y(y, r)
    wand = kabel + r * (P.SPIEL + P.TURM_WAND + P.KANAL_ABSTAND + P.KANAL_WAND)
    innen = wand + r * P.KANAL_INNEN[0]
    return min(wand, innen), max(wand, innen)


def kanal_hoehe():
    return P.PLATTE_DICKE + P.KANAL_INNEN[1]


def austritt_x():
    """Lücke links hinten zwischen Pfostenhülse und äußerstem B-Halter: hier gehen
    USB- und Netzteilkabel über die Hinterkante raus (Wert für die linke Seite)."""
    h = P.PFOSTEN + 2 * P.SPIEL + 2 * P.HUELSE_WAND
    huelse_innen = LEISTE_X0 + h
    halter_aussen = min(P.STRAHLEN_B) - TURM_X / 2
    if halter_aussen - huelse_innen < 9:
        raise ValueError("Kein Platz für den Kabelaustritt zwischen Pfosten und B-Halter")
    return (huelse_innen + halter_aussen) / 2


def _kanal(y, xs):
    r, w, c, d = richtung(y), P.KANAL_WAND, P.KANAL_CLIP, P.PLATTE_DICKE
    i0, i1 = kanal_y(y)
    oben = kanal_hoehe()
    form = quader(LEISTE_X0, LEISTE_X1, i0 - w, i1 + w, 0, oben)
    form -= quader(LEISTE_X0 - 1, LEISTE_X1 + 1, i0, i1, d, oben + 1)
    form += quader(LEISTE_X0, LEISTE_X1, i0, i0 + c, oben - c, oben)
    form += quader(LEISTE_X0, LEISTE_X1, i1 - c, i1, oben - c, oben)
    # Einführschlitz vor jedem Halter (Halterseite) und Öffnung zum Nest (Mittenseite)
    halter = (i0 - w - 0.1, i0 + c + 0.1) if r > 0 else (i1 - c - 0.1, i1 + w + 0.1)
    mitte = (i1 - c - 0.1, i1 + w + 0.1) if r > 0 else (i0 - w - 0.1, i0 + c + 0.1)
    # dazu: vor den Pfosten (Adern in den Pfosten) und an der Austrittsstelle (USB, 5 V)
    extra = [px for px, py in pfosten_xy() if py == y] + [s * austritt_x() for s in (-1, 1)]
    for x in list(xs) + extra:
        form -= quader(x - P.EINFUEHRUNG / 2, x + P.EINFUEHRUNG / 2, *halter, d, oben + 1)
    nx0, nx1, _, _ = nest_layout()["aussen"]
    form -= quader(nx0, nx1, *mitte, d, oben + 1)
    return form


# ---------------------------------------------------------------------------
# Elektronik-Nest: Pico auf Schraubklemmen-Board + Wago-Reihen, liegt mittig
# zwischen den Kanälen auf den Rippen (Platten-Koordinaten, Boden auf z=PLATTE_DICKE)
# ---------------------------------------------------------------------------
def wago_anzahl(leiter):
    """Wago 221-415 hat 5 Plätze; beim Verketten kostet jede Brücke 2 Plätze."""
    k = 1
    while 3 * k + 2 < leiter:
        k += 1
    return k


def seite(x):
    return "links" if x <= 0 else "rechts"


def nest_leiter():
    """Leiter je Wago-Reihe (Platten-Koordinaten). Sensoren gehen auf ihre Seite, beide Seiten
    sind über eine Brücke verbunden. Unten links zusätzlich Netzteil, Zuleitung nach oben und
    Pico-GND; oben kommt die Zuleitung rechts an (die obere Platte ist gespiegelt)."""
    n = {s: sum(1 for _, xs in EBENEN for x in xs if seite(x) == s) for s in ("links", "rechts")}
    # + je Seite eine Leitung zum LED-Streifen dieser Seite
    # links zusätzlich der Kondensator 1000 µF am Netzteil-Eingang (+ an 5V, − an GND)
    unten = {("links", "5V"): n["links"] + 3 + 1 + 1, ("links", "GND"): n["links"] + 4 + 1 + 1,
             ("rechts", "5V"): n["rechts"] + 1 + 1, ("rechts", "GND"): n["rechts"] + 1 + 1}
    oben = {("links", "5V"): n["links"] + 1, ("links", "GND"): n["links"] + 1,
            ("rechts", "5V"): n["rechts"] + 2, ("rechts", "GND"): n["rechts"] + 2}
    return {"unten": unten, "oben": oben}


def nest_layout():
    s, w = P.SPIEL, P.NEST_WAND
    bl, bb, _ = P.PICO_BOARD
    wb, wl, _ = P.WAGO
    leiter = nest_leiter()
    k = {sd: max(wago_anzahl(leiter[pl][(sd, bus)]) for pl in leiter for bus in ("5V", "GND"))
         for sd in ("links", "rechts")}
    breite_seite = {sd: k[sd] * wb + 2 * s for sd in k}
    breite = w + breite_seite["links"] + w + bl + 2 * s + w + breite_seite["rechts"] + w
    reihe = wl + 2 * s
    tiefe = max(bb + 2 * s, 2 * reihe + w) + 2 * w
    y0 = kanal_y(Y_A)[1] + P.KANAL_WAND + 1
    y1 = kanal_y(Y_B)[0] - P.KANAL_WAND - 1
    if tiefe > y1 - y0:
        raise ValueError(f"Nest ({tiefe:.0f} mm) passt nicht zwischen die Kanäle ({y1 - y0:.0f} mm)")
    ym = (y0 + y1) / 2
    x0 = -breite / 2
    xl = (x0 + w, x0 + w + breite_seite["links"])
    board = (xl[1] + w, xl[1] + w + bl + 2 * s, ym - (bb + 2 * s) / 2, ym + (bb + 2 * s) / 2)
    xr = (board[1] + w, board[1] + w + breite_seite["rechts"])
    wago = {}
    for sd, (a, b) in (("links", xl), ("rechts", xr)):
        wago[(sd, "5V")] = (a, b, ym + w / 2, ym + w / 2 + reihe)
        wago[(sd, "GND")] = (a, b, ym - w / 2 - reihe, ym - w / 2)
    lasche = P.SCHRAUBAUGE_D
    # Druckteilung (ganz wäre das Nest länger als das Druckbett): an der Innenseite der linken Boardwand
    return {"aussen": (x0 - lasche, -x0 + lasche, ym - tiefe / 2, ym + tiefe / 2), "board": board,
            "wago": wago, "k": k, "ym": ym, "schnitt": board[0],
            "schrauben": [(x0 - lasche / 2, ym), (-x0 + lasche / 2, ym)][:P.NEST_SCHRAUBEN]}


def schraub_rippen():
    """Rippen, deren Schraubauge frei liegt (unter dem Nest wird nicht geschraubt)."""
    nx0, nx1, _, _ = nest_layout()["aussen"]
    rand = P.SCHRAUBAUGE_D / 2 + 1
    return [x for x in rippen_x() if x < nx0 - rand or x > nx1 + rand]


def elektronik_nest():
    """Druckteil, Platten-Koordinaten mit Boden auf z=0 (wird auf die Rippen gelegt)."""
    L = nest_layout()
    x0, x1, y0, y1 = L["aussen"]
    s, w, b, h = P.SPIEL, P.NEST_WAND, P.NEST_BODEN, P.NEST_HOEHE
    form = quader(x0, x1, y0, y1, 0, b)
    taschen = [L["board"]] + list(L["wago"].values())
    for tx0, tx1, ty0, ty1 in taschen:
        form += quader(tx0 - w, tx1 + w, ty0 - w, ty1 + w, 0, b + h)
    for tx0, tx1, ty0, ty1 in taschen:
        form -= quader(tx0, tx1, ty0, ty1, b, b + h + 1)
        # Kabeldurchlässe in den Taschenwänden vorne und hinten
        xm = (tx0 + tx1) / 2
        form -= quader(xm - (tx1 - tx0) * 0.35, xm + (tx1 - tx0) * 0.35, ty0 - w - 1, ty1 + w + 1, b + 3, b + h + 1)
    for x, y in L["schrauben"]:
        form -= zyl_z(x, y, -1, b + 1, P.SCHRAUBE_D)
    return form


def nest_teile():
    """Nest in zwei Druckteile (links: Wagos + linke Boardwand, rechts: Board + Wagos), im Boden
    mit zwei Schwalbenschwänzen verbunden und verklebt wie die Sensorplatte."""
    L = nest_layout()
    n, t, ym = elektronik_nest(), L["schnitt"], L["ym"]
    zapfen = [ym - 15, ym + 15]
    links = n & quader(-1000, t, -1000, 1000, -10, 100)
    rechts = n & quader(t, 1000, -1000, 1000, -10, 100)
    for y in zapfen:
        links += n & _schwalbe(t, y)
        rechts -= _schwalbe(t, y, P.SCHWALBE_SPIEL)
    return [links, rechts]


def sensorplatte():
    """Ganze Platte über die volle Breite (danach mit zerteilen() in Druckstücke schneiden)."""
    sb, d = P.STREIFEN_BREITE, P.PLATTE_DICKE
    y_hinten = Y_B + sb / 2
    y_vorne = -P.LIPPE_DICKE if P.MIT_LIPPE else Y_A - sb / 2
    y_schraube = (Y_A + Y_B) / 2
    form = quader(LEISTE_X0, LEISTE_X1, Y_A - sb / 2, Y_A + sb / 2, 0, d)
    form += quader(LEISTE_X0, LEISTE_X1, Y_B - sb / 2, Y_B + sb / 2, 0, d)
    if P.MIT_LIPPE:
        form += quader(LEISTE_X0, LEISTE_X1, -P.LIPPE_DICKE, 0, -P.LIPPE_TIEFE, d)
    for x in rippen_x():
        form += quader(x - P.RIPPE_BREITE / 2, x + P.RIPPE_BREITE / 2, y_vorne, y_hinten, 0, d)
    for x in schraub_rippen():
        form += zyl_z(x, y_schraube, 0, d, P.SCHRAUBAUGE_D)
    for y, xs in EBENEN:
        form += _kanal(y, xs)
        for x in xs:
            form += _turm(x, y, richtung(y))
    for x, y in pfosten_xy():
        form += _huelse(x, y)
    for x, y in deckel_saeulen():
        form += _saeule(x, y)
    for y, xs in EBENEN:
        for x in xs:
            form -= _sensor_loch(x, y, richtung(y))
            form -= _kabelkerbe(x, y, richtung(y))
    for x, y in pfosten_xy():
        form -= _huelse(x, y, loch=True)
    for x, y in deckel_saeulen():
        form -= _saeule(x, y, loch=True)
    for x in schraub_rippen():
        form -= zyl_z(x, y_schraube, -1, d + 1, P.SCHRAUBE_D)
    return form


def _schwalbe(t, y, spiel=0.0):
    """Schwalbenschwanz in einem Streifen: sitzt am linken Stück und greift ins rechte."""
    l, b0, b1 = P.SCHWALBE
    flaeche = Polygon((t - 0.5, y - b0 / 2 - spiel), (t + l + spiel, y - b1 / 2 - spiel),
                      (t + l + spiel, y + b1 / 2 + spiel), (t - 0.5, y + b0 / 2 + spiel), align=None)
    return Pos(0, 0, -1) * extrude(flaeche, amount=P.PLATTE_DICKE + 2)


def zerteilen(platte):
    """Platte an den Trennfugen in druckbare Stücke schneiden (von links nach rechts).
    Die Stücke greifen über Schwalbenschwänze in den Streifen ineinander."""
    stuecke = []
    for i, (a, b) in enumerate(leisten_stuecke()):
        s = platte & quader(a - (1 if i == 0 else 0), b, -1000, 1000, -50, 200)
        for y, _ in EBENEN:
            if b in P.LEISTE_TEILUNGEN:                       # rechte Fuge: Zapfen dran
                s += platte & _schwalbe(b, y)
            if a in P.LEISTE_TEILUNGEN:                       # linke Fuge: Aussparung
                s -= _schwalbe(a, y, P.SCHWALBE_SPIEL)
        stuecke.append(s)
    return stuecke


def pfosten(z_unten, z_oben):
    """Alu-Vierkantrohre zwischen den Platten (Rahmen-Koordinaten)."""
    p = P.PFOSTEN
    return [teil(quader(x - p / 2, x + p / 2, y - p / 2, y + p / 2, z_unten, z_oben),
                 "Pfosten Alu 10x10", "alu") for x, y in pfosten_xy()]


def testblock():
    """Prototyp: 3 Sensoren im B-Abstand, gleiche Türmchen wie die echte Platte.
    2x drucken, im Abstand FENSTER_HOEHE gegenüber aufstellen, Übersprechen testen."""
    abst = P.STRAHLEN_B[1] - P.STRAHLEN_B[0]
    xs = [-abst, 0, abst]
    x0, x1 = -abst - 25, abst + 25
    sb, d = P.STREIFEN_BREITE, P.PLATTE_DICKE
    augen = (x0 + P.SCHRAUBAUGE_D / 2 + 1, x1 - P.SCHRAUBAUGE_D / 2 - 1)
    form = quader(x0, x1, -sb / 2, sb / 2, 0, d)
    for x in xs:
        form += _turm(x, 0, 1)
    for x in xs:
        form -= _sensor_loch(x, 0, 1)
        form -= _kabelkerbe(x, 0, 1)
    for x in augen:
        form -= zyl_z(x, 0, -1, d + 1, P.SCHRAUBE_D)
    return form


def sensoren_und_strahlen(z_unten, z_oben):
    """Liegende Sensorgehäuse mit LED-Kuppe (unten Empfänger, oben Sender) und Strahlen."""
    teile = []
    b, h, k = P.SENSOR_BREITE, P.SENSOR_HOEHE, P.LED_UEBERSTAND
    loch_d = P.SCHRAUBE_SENSOR[0] + 0.3
    for y, xs in EBENEN:
        y0, y1, _, loch = gehaeuse_y(y, richtung(y))
        for x in xs:
            empf = quader(x - b / 2, x + b / 2, y0, y1, z_unten, z_unten + h) + \
                zyl_z(x, y, z_unten + h, z_unten + h + k, P.LED_DURCHMESSER)
            empf -= zyl_z(x, loch, z_unten - 1, z_unten + h + 1, loch_d)
            send = quader(x - b / 2, x + b / 2, y0, y1, z_oben - h, z_oben) + \
                zyl_z(x, y, z_oben - h - k, z_oben - h, P.LED_DURCHMESSER)
            send -= zyl_z(x, loch, z_oben - h - 1, z_oben + 1, loch_d)
            teile.append(teil(empf, "Empfänger", "sensor"))
            teile.append(teil(send, "Sender", "sensor"))
            teile.append(teil(zyl_z(x, y, z_unten + LEISTE_DICKE, z_oben - LEISTE_DICKE, 1.5),
                              "IR-Strahl (Darstellung)", "strahl"))
    return teile


# ---------------------------------------------------------------------------
# Rahmen (Rahmen-Koordinaten: Vorderkante y=0, Unterseite z=0, Mitte x=0)
# ---------------------------------------------------------------------------
def led_lage(s):
    """LED-Streifen auf der Vorderseite des vorderen Pfostens der Seite s (-1 links, +1 rechts):
    (x-Mitte, y Vorderseite Pfosten, z0, z1) in Rahmen-Koordinaten – zwischen den Pfostenhülsen."""
    px, py = next((x, y) for x, y in pfosten_xy() if y == Y_A and x * s > 0)
    rand = P.PLATTE_DICKE + P.HUELSE_HOEHE + 2
    return px, py - P.PFOSTEN / 2, T + rand, AUSSEN_H - T - rand


def led_anzahl():
    _, _, z0, z1 = led_lage(1)
    return int((z1 - z0) / 1000 * P.LED_PRO_M)


def led_streifen(s):
    x, yv, z0, _ = led_lage(s)
    b, d = P.LED_STREIFEN
    n = led_anzahl()
    schritt = 1000 / P.LED_PRO_M
    form = quader(x - b / 2, x + b / 2, yv - d, yv, z0, z0 + n * schritt)
    for i in range(n):
        zm = z0 + (i + 0.5) * schritt
        form += quader(x - 2.5, x + 2.5, yv - d - 1.5, yv - d, zm - 2.5, zm + 2.5)
    return form


# ---------------------------------------------------------------------------
# Deckel über dem Mittelfeld: versteckt Nest, Wagos und Adern. Liegt auf Säulen der
# Sensorplatte, unterhalb der Strahlen. Platten-Koordinaten (z=0 auf dem Brett).
# ---------------------------------------------------------------------------
def deckel_lage():
    """(x0, x1, y0, y1, z_unten) des Deckels."""
    hoechst = max(P.PLATTE_DICKE + P.NEST_BODEN + P.WAGO[2],
                  P.PLATTE_DICKE + P.NEST_BODEN + P.PICO_BOARD[2],          # Brücken laufen neben dem Board
                  kanal_hoehe())
    z0 = hoechst + P.DECKEL_LUFT
    if z0 + P.DECKEL_DICKE > LEISTE_DICKE:
        raise ValueError("Deckel ragt über die Sensorhalter in die Strahlen")
    y0 = kanal_y(Y_A)[0] - P.KANAL_WAND
    y1 = kanal_y(Y_B)[1] + P.KANAL_WAND
    return LEISTE_X0, LEISTE_X1, y0, y1, z0


def deckel_saeulen():
    """Säulen auf den äußersten Rippen, je vorne und hinten im Mittelfeld."""
    _, _, y0, y1, _ = deckel_lage()
    rand = P.KANAL_INNEN[0] + 2 * P.KANAL_WAND + P.DECKEL_SAEULE_D / 2 + 2
    xs = (min(rippen_x()), max(rippen_x()))
    return [(x, y) for x in xs for y in (y0 + rand, y1 - rand)]


def _saeule(x, y, loch=False):
    z0 = deckel_lage()[4]
    if loch:
        return zyl_z(x, y, z0 - 15, z0 + 1, 2.2)                  # für Holzschraube 2,5 (selbstschneidend)
    return zyl_z(x, y, 0, z0, P.DECKEL_SAEULE_D)


def deckel():
    """Ganzer Deckel (wird wie die Platte an den Trennfugen geteilt)."""
    x0, x1, y0, y1, z0 = deckel_lage()
    form = quader(x0, x1, y0, y1, z0, z0 + P.DECKEL_DICKE)
    for x, y in deckel_saeulen():
        form -= zyl_z(x, y, z0 - 1, z0 + P.DECKEL_DICKE + 1, P.SCHRAUBE_SENSOR[0] + 0.3)
    return form


def deckel_haelften():
    return [deckel() & quader(a - (1 if i == 0 else 0), b + (1 if i == len(leisten_stuecke()) - 1 else 0),
                              -1000, 1000, -50, 200)
            for i, (a, b) in enumerate(leisten_stuecke())]



# ---------------------------------------------------------------------------
# Kabelkanal außen am linken Seitenbrett, hinten (Rahmen-Koordinaten)
# ---------------------------------------------------------------------------
def kabelkanal_lage():
    """(x0, x1, y0, y1) der Außenkontur; offene Seite zeigt nach außen (-x)."""
    b, t = P.KABELKANAL_INNEN
    w = P.KABELKANAL_WAND
    x1 = -(W / 2 + T)
    y1 = TIEFE - P.KABELKANAL_RAND_HINTEN
    return x1 - t - w, x1, y1 - b - 2 * w, y1


def kabelkanal_mitte():
    x0, x1, y0, y1 = kabelkanal_lage()
    return (x0 + x1) / 2, (y0 + y1) / 2


def kabelkanal():
    """U-Profil mit Rastlippen, ganze Höhe der Kiste; Schraublöcher in den Rücken."""
    x0, x1, y0, y1 = kabelkanal_lage()
    w = P.KABELKANAL_WAND
    form = quader(x0, x1, y0, y1, 0, AUSSEN_H) - quader(x0 - 1, x1 - w, y0 + w, y1 - w, -1, AUSSEN_H + 1)
    form += quader(x0, x0 + w, y0 + w, y0 + w + 2, 0, AUSSEN_H) + quader(x0, x0 + w, y1 - w - 2, y1 - w, 0, AUSSEN_H)
    for z in (40, AUSSEN_H / 2 - 40, AUSSEN_H / 2 + 40, AUSSEN_H - 40):
        form -= zyl_x(x1 - w - 1, x1 + 1, (y0 + y1) / 2, z, P.SCHRAUBE_D)
    return form


def kabelkanal_teile():
    h = AUSSEN_H / 2
    return [kabelkanal() & quader(-1000, 1000, -1000, 1000, a, b) for a, b in ((-1, h), (h, AUSSEN_H + 1))]


def rahmen():
    teile = []
    xi = W / 2
    teile.append(teil(quader(-xi, xi, 0, TIEFE, 0, T), "Brett unten", "holz"))
    teile.append(teil(quader(-xi, xi, 0, TIEFE, AUSSEN_H - T, AUSSEN_H), "Brett oben", "holz"))
    for s in (-1, 1):
        brett = quader(min(s * xi, s * (xi + T)), max(s * xi, s * (xi + T)), 0, TIEFE, 0, AUSSEN_H)
        teile.append(teil(brett, f"Seitenbrett {'rechts' if s > 0 else 'links'}", "holz_dunkel"))

    for nr, k in enumerate(kabelkanal_teile(), 1):
        teile.append(teil(k, f"Kabelkanal Teil {nr} (Druckteil)", "deckel"))

    # LED-Streifen auf den vorderen Alu-Pfosten
    for s in (-1, 1):
        teile.append(teil(led_streifen(s), f"LED-Streifen {'rechts' if s > 0 else 'links'} "
                                           f"({led_anzahl()}x WS2812B)", "led"))

    # Schwimmnudeln an den vorderen Innenkanten (geschlitzt, über die Brettkante geschoben)
    r, ri = P.SCHWIMMNUDEL_D / 2, 10
    ym = 5
    nudeln = []
    for z in (T / 2, AUSSEN_H - T / 2):
        nudeln.append(zyl_x(-xi - T, xi + T, ym, z, P.SCHWIMMNUDEL_D) - zyl_x(-xi - T - 1, xi + T + 1, ym, z, 2 * ri))
    for s in (-1, 1):
        x = s * (xi + T / 2)
        nudeln.append(zyl_z(x, ym, T, AUSSEN_H - T, P.SCHWIMMNUDEL_D) - zyl_z(x, ym, 0, AUSSEN_H, 2 * ri))
    for n in nudeln:
        teile.append(teil(n, "Schwimmnudel", "schaum"))

    # Weiche Trennung in Ebene A
    teile.append(teil(quader(-P.TRENNUNG_A_BREITE / 2, P.TRENNUNG_A_BREITE / 2,
                             Y_A - P.TRENNUNG_A_TIEFE / 2, Y_A + P.TRENNUNG_A_TIEFE / 2,
                             T + LEISTE_DICKE, AUSSEN_H - T - LEISTE_DICKE),
                      "Trennung Ebene A (Schaumstoff)", "trennung"))

    # Sensorplatten: unten wie konstruiert, oben um Y gedreht
    def platzieren(form, oben):
        if oben:
            return Pos(0, 0, AUSSEN_H - T) * Rot(0, 180, 0) * form
        return Pos(0, 0, T) * form

    stuecke = zerteilen(sensorplatte())
    for oben in (False, True):
        for nr, h in enumerate(stuecke, 1):
            teile.append(teil(platzieren(h, oben),
                              f"Sensorplatte Teil {nr} ({'oben' if oben else 'unten'})",
                              ("druck", "druck_c")[nr % 2]))

    for oben in (False, True):
        for nr, h in enumerate(deckel_haelften(), 1):
            teile.append(teil(platzieren(h, oben), f"Deckel Teil {nr} ({'oben' if oben else 'unten'})", "deckel"))
    teile += pfosten(T + P.PLATTE_DICKE, AUSSEN_H - T - P.PLATTE_DICKE)
    teile += sensoren_und_strahlen(T, AUSSEN_H - T)
    return teile


def flansch(x, y, z_platte_oben):
    pb, pt, ph = P.FLANSCH_PLATTE
    d, l = P.FLANSCH_TOPF
    f = quader(x - pb / 2, x + pb / 2, y - pt / 2, y + pt / 2, z_platte_oben - ph, z_platte_oben)
    f += zyl_z(x, y, z_platte_oben - ph - l, z_platte_oben - ph, d)
    return teil(f, "Boxenflansch", "flansch")


def stativ(x, y, kopf_z, bein_winkel):
    teile = []
    oben = min(kopf_z - 300, 1000)
    teile.append(teil(zyl_z(x, y, 150, oben, P.STATIV_UNTERROHR_D), "Stativ Unterrohr", "stahl"))
    teile.append(teil(zyl_z(x, y, oben - 50, kopf_z, P.STATIV_ROHR_D), "Stativ Rohr 35 mm", "alu"))
    for wink in bein_winkel:
        a = math.radians(wink)
        fx, fy = x + P.STATIV_BEIN_RADIUS * math.cos(a), y + P.STATIV_BEIN_RADIUS * math.sin(a)
        teile.append(teil(stab((x, y, P.STATIV_SPINNE_Z), (fx, fy, 15), 22), "Stativbein", "stahl"))
        teile.append(teil(Pos(fx - 60 * math.cos(a), fy - 60 * math.sin(a), 40) * Rot(0, 0, wink)
                          * Box(260, 140, 80), "Sandsack", "sand"))
        # Leuchtband auf dem Bein
        m = 0.55
        teile.append(teil(stab((x + (fx - x) * m, y + (fy - y) * m, P.STATIV_SPINNE_Z * (1 - m) + 15 * m),
                               (x + (fx - x) * (m + 0.12), y + (fy - y) * (m + 0.12),
                                P.STATIV_SPINNE_Z * (1 - m - 0.12) + 15 * (m + 0.12)), 24),
                          "Leuchtband", "klebeband"))
    return teile


def verschieben(teile, dx, dy, dz):
    neu = []
    for t in teile:
        m = Pos(dx, dy, dz) * t
        m.label, m.color = t.label, t.color
        neu.append(m)
    return neu


def faust_und_umgebung(fenster_mitte_z, seite=-1):
    """Darstellung: Faust in Ebene A, Unterarm, Bodenmarkierung."""
    x = seite * 65
    teile = [
        teil(Pos(x, Y_A, fenster_mitte_z) * Sphere(32), "Faust (Darstellung)", "haut"),
        teil(stab((x * 1.6, Y_A - 380, fenster_mitte_z - 30), (x, Y_A - 20, fenster_mitte_z), 55),
             "Unterarm (Darstellung)", "haut"),
        teil(quader(-250, 250, P.STANDMARKE_Y - 25, P.STANDMARKE_Y + 25, 0, 1),
             "Standmarke Klebeband", "klebeband"),
    ]
    return teile


# ---------------------------------------------------------------------------
# Gesamtaufbauten
# ---------------------------------------------------------------------------
def fenster_mitte_im_rahmen():
    return T + LEISTE_DICKE + P.FENSTER_HOEHE / 2


def _aufbau(fenstermitte, titel):
    """Kiste sitzt mit dem Boxenflansch oben auf dem 35-mm-Stativ (kein Hängewinkel)."""
    rz = fenstermitte - fenster_mitte_im_rahmen()
    kopf = rz - P.FLANSCH_PLATTE[2]
    import elektronik as E                      # spät importiert: elektronik baut auf modell auf
    import pult as PU
    teile = verschieben(rahmen() + E.schrauben() + E.elektronik() + PU.pult_teile(), 0, 0, rz)
    teile.append(flansch(0, TIEFE / 2, rz))
    teile += stativ(0, TIEFE / 2, kopf, (90, 210, 330))
    teile += faust_und_umgebung(fenstermitte)
    return Compound(children=teile, label=titel), {"stativkopf": kopf, "rahmen_unten": rz}


def aufbau_erwachsene():
    return _aufbau(P.ERW_FENSTERMITTE, "Aufbau Erwachsene")


def aufbau_kinder():
    return _aufbau(P.KIND_FENSTERMITTE, "Aufbau Kinder")
