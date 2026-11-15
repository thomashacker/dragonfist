"""
Bedienpult oben auf der Kiste: keilförmiges Druckgehäuse mit 7"-Display im Wire-Mod-Rahmen
(20° nach hinten geneigt, zum Kind), schräger Knopfleiste mit Arcade-Knöpfen davor, Jetson Orin Nano
auf der Bodenplatte. Der USB-Lautsprecher steht außen rechts neben dem Pult auf der Kiste (nichts zu drucken).

Pult-Koordinaten: x quer (Mitte 0), y nach hinten (Vorderkante 0), z nach oben (Brett-Oberseite 0).
Druckteile: Gehäuse (mit Stützen drucken, Knopfleiste ist flach geneigt) und Bodenplatte.
"""
import math

from build123d import Box, Plane, Polygon, Pos, extrude, offset

import modell as M
import parameter as P
from modell import quader, teil, zyl_z

W, D, WAND = P.PULT_BREITE, P.PULT_TIEFE, P.PULT_WAND
PROFIL = P.PULT_PROFIL


def _profil_koerper(punkte, x0, x1):
    flaeche = Polygon(*punkte, align=None)
    # Plane.YZ zeigt mit der Normalen nach -x: daher am rechten Ende ansetzen
    return Pos(x1, 0, 0) * extrude(Plane.YZ * flaeche, amount=x1 - x0)


def _flaeche(i):
    """Schräge Fläche zwischen Profilpunkt i und i+1: (Mitte (y, z), Richtung nach oben, Normale nach außen)."""
    (y0, z0), (y1, z1) = PROFIL[i], PROFIL[i + 1]
    l = math.hypot(y1 - y0, z1 - z0)
    hoch = ((y1 - y0) / l, (z1 - z0) / l)
    normale = (-hoch[1], hoch[0])                       # nach vorne/oben (Profil läuft gegen den Uhrzeigersinn)
    return ((y0 + y1) / 2, (z0 + z1) / 2), hoch, normale, l


def _auf_flaeche(i, form, x=0.0, entlang=0.0, normal=0.0):
    """Form (lokal: x quer, y entlang der Fläche nach oben, z = Normale) auf Fläche i setzen."""
    (ym, zm), hoch, n, _ = _flaeche(i)
    ursprung = (x, ym + hoch[0] * entlang + n[0] * normal, zm + hoch[1] * entlang + n[1] * normal)
    return Plane(origin=ursprung, x_dir=(1, 0, 0), z_dir=(0, n[0], n[1])) * form


KNOPF_FLAECHE, DISPLAY_FLAECHE = 1, 2


def knopf_x():
    n = len(P.KNOEPFE)
    return [(i - (n - 1) / 2) * P.KNOPF_ABSTAND for i in range(n)]


def jetson_lage():
    l, b, h = P.JETSON
    yc = D - WAND - 8 - b / 2
    return (-l / 2, l / 2, yc - b / 2, yc + b / 2, WAND + 6, WAND + 6 + h)


def lautsprecher_lage():
    """Außen rechts neben dem Pult, vorne, Lautsprecher zum Kind; mit 2 Schrauben durch die Ösen ins Brett."""
    b, t, h = P.LAUTSPRECHER
    x0 = W / 2 + 8
    if x0 + b > M.AUSSEN_W / 2:
        raise ValueError("Lautsprecher ragt über die Kiste hinaus")
    return (x0, x0 + b, 10, 10 + t, 0, h)


def gehaeuse():
    aussen = _profil_koerper(PROFIL, -W / 2, W / 2)
    innen_profil = offset(Polygon(*PROFIL, align=None), -WAND)
    innen = Pos(W / 2 - WAND, 0, 0) * extrude(Plane.YZ * innen_profil, amount=W - 2 * WAND)
    form = aussen - innen
    form -= quader(-W / 2 + WAND, W / 2 - WAND, WAND, D - WAND, -1, WAND + 0.5)      # unten offen
    # Display-Fenster mit erhabenem Wire-Mod-Rahmen und Eckschrauben
    fb, fh = P.DISPLAY_FENSTER
    (_, _, _, l) = _flaeche(DISPLAY_FLAECHE)
    rahmen = _auf_flaeche(DISPLAY_FLAECHE, Box(fb + 28, min(fh + 28, l - 4), 4), normal=2)
    form += rahmen
    form -= _auf_flaeche(DISPLAY_FLAECHE, Box(fb, fh, 30))
    for sx in (-1, 1):
        for sy in (-1, 1):
            form += _auf_flaeche(DISPLAY_FLAECHE, zyl_z(0, 0, 0, 2, 7), x=sx * (fb / 2 + 7),
                                 entlang=sy * (min(fh + 28, l - 4) / 2 - 7), normal=4)
    # Knopflöcher
    for x in knopf_x():
        form -= _auf_flaeche(KNOPF_FLAECHE, zyl_z(0, 0, -20, 20, P.KNOPF_LOCH), x=x)
    # Lüftungsschlitze oben über dem Jetson
    jx0, jx1, jy0, jy1, _, _ = jetson_lage()
    z_oben = max(z for _, z in PROFIL)
    for i in range(6):
        y = jy0 + 8 + i * (jy1 - jy0 - 16) / 5
        form -= quader(jx0 + 10, jx1 - 10, y - 2, y + 2, z_oben - WAND - 1, z_oben + 1)
    # Rückwand: Anschlüsse des Jetson (Strom, USB, DisplayPort) und Kabel vom Pico
    form -= quader(jx0 - 2, jx1 + 2, D - WAND - 1, D + 1, WAND + 3, WAND + 6 + P.JETSON[2] + 4)
    # Schrauben seitlich in die Eckblöcke der Bodenplatte
    for x, y in _eckbloecke():
        s = 1 if x > 0 else -1
        form -= Pos(s * W / 2, y, WAND + 6) * Plane.YZ * zyl_z(0, 0, -WAND - 1, WAND + 1, 3.4)
    return form


def _eckbloecke():
    # vorne hinter den Knopfkörpern, hinten vor der Rückwand
    return [(s * (W / 2 - WAND - 6), y) for s in (-1, 1) for y in (75, D - WAND - 22)]


def boden():
    """Bodenplatte innen im Gehäuse: Jetson-Abstandshalter, Eckblöcke, Löcher fürs Brett."""
    form = quader(-W / 2 + WAND + 0.3, W / 2 - WAND - 0.3, WAND + 0.3, D - WAND - 0.3, 0, WAND)
    for x, y in _eckbloecke():
        form += quader(x - 6, x + 6, y - 6, y + 6, 0, WAND + 12)
        form -= Pos(x, y, WAND + 6) * Plane.YZ * zyl_z(0, 0, -7, 7, 2.6)              # M3 selbstschneidend
    jx0, jx1, jy0, jy1, jz0, _ = jetson_lage()
    lx, ly = P.JETSON_LOECHER
    cx, cy = (jx0 + jx1) / 2, (jy0 + jy1) / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            form += zyl_z(cx + sx * lx / 2, cy + sy * ly / 2, 0, jz0, 7)
            form -= zyl_z(cx + sx * lx / 2, cy + sy * ly / 2, 1, jz0 + 1, 2.2)       # M2.5 selbstschneidend
    for x, y in ((-W / 2 + 25, WAND + 12), (W / 2 - 25, WAND + 12), (0, D - WAND - 12)):
        form -= zyl_z(x, y, -1, WAND + 1, P.SCHRAUBE_D)                              # 4x16 ins Brett
    for i in range(4):                                                               # Luft von unten
        y = jy0 + 10 + i * (jy1 - jy0 - 20) / 3
        form -= quader(jx0 + 15, jx1 - 15, y - 2, y + 2, -1, WAND + 1)
    return form


def einbauteile():
    """Display, Jetson, Lautsprecher, Knöpfe, USB-Encoder in Pult-Koordinaten (zur Darstellung)."""
    teile = []
    b, h, t = P.DISPLAY
    teile.append(teil(_auf_flaeche(DISPLAY_FLAECHE, Box(b, h, t), normal=-WAND - t / 2), "Display 7 Zoll (HDMI)",
                      "sensor"))
    fb, fh = P.DISPLAY_FENSTER
    teile.append(teil(_auf_flaeche(DISPLAY_FLAECHE, Box(fb - 2, fh - 2, 0.6), normal=-WAND + 0.5),
                      "Display Bildfläche", "bildschirm"))
    teile.append(teil(quader(*jetson_lage()), "Jetson Orin Nano", "platine"))
    teile.append(teil(quader(*lautsprecher_lage()), "USB-Lautsprecher", "usb"))
    for x, name in zip(knopf_x(), P.KNOEPFE):
        farbe = "knopf_start" if name == "START" else "knopf"
        knopf = (_auf_flaeche(KNOPF_FLAECHE, zyl_z(0, 0, 0, 8, 30), x=x) +
                 _auf_flaeche(KNOPF_FLAECHE, zyl_z(0, 0, -WAND - P.KNOPF_TIEFE, 0, 24), x=x))
        teile.append(teil(knopf, f"Arcade-Knopf {name}", farbe))
    jy0 = jetson_lage()[2]
    teile.append(teil(quader(-35, 35, jy0 - 34, jy0 - 4, WAND, WAND + 8), "USB-Encoder (Knöpfe -> Jetson)", "platine"))
    return teile


def lage_auf_kiste():
    """Verschiebung Pult -> Rahmen-Koordinaten: mittig auf dem oberen Brett."""
    return 0, (M.TIEFE - D) / 2, M.AUSSEN_H


def pult_teile():
    dx, dy, dz = lage_auf_kiste()
    teile = [teil(gehaeuse(), "Pult Gehäuse (Druckteil)", "deckel"),
             teil(boden(), "Pult Boden (Druckteil)", "druck")] + einbauteile()
    return M.verschieben(teile, dx, dy, dz)
