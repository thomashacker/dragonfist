"""
Prüfdruck: kleine Ausschnitte aus den echten Druckteilen, um die wichtigsten Passungen
mit den echten Teilen zu testen, bevor alles gedruckt wird (python build.py exportiert sie
nach ausgabe/pruefdruck/).

Jeder Ausschnitt ist mit derselben Funktion gebaut wie das Endteil: passt der Prüfdruck,
passt auch das Endteil. Passt er nicht, Maß in parameter.py ändern und neu bauen.
"""
from build123d import Cylinder, Pos, Rot, extrude

import modell as M
import parameter as P
import pult as PU
from modell import quader


def _ausschnitt(form, x0, x1, y0, y1, z0=-200, z1=400):
    return form & quader(x0, x1, y0, y1, z0, z1)


def sensor_tasche():
    """Ein Türmchen aus dem Testblock: Tasche, Lichtloch, Schraubloch, Kabelkerbe."""
    a = M.TURM_X / 2 + 4
    return _ausschnitt(M.testblock(), -a, a, -100, 100)


def huelsen_ecke():
    """Linke vordere Ecke der Sensorplatte: Pfostenhülse mit Kabelschlitz, Stück Kabelkanal."""
    teil1 = M.zerteilen(M.sensorplatte())[0]
    x, y = next((x, y) for x, y in M.pfosten_xy() if x < 0 and y == M.Y_A)
    return _ausschnitt(teil1, M.LEISTE_X0 - 1, x + 30, y - 20, y + 30)


def schwalben_fuge():
    """Beide Seiten einer Fuge im Streifen A: Schwalbenschwanz zusammenstecken."""
    t = P.LEISTE_TEILUNGEN[0]
    sb = P.STREIFEN_BREITE
    links, rechts = M.zerteilen(M.sensorplatte())[:2]
    y0, y1 = M.Y_A - sb / 2 - 0.5, M.Y_A + sb / 2 + 0.5
    return (_ausschnitt(links, t - 25, t + P.SCHWALBE[0] + 1, y0, y1, z1=P.PLATTE_DICKE + 0.5),
            _ausschnitt(rechts, t - 1, t + 25, y0, y1, z1=P.PLATTE_DICKE + 0.5))


def knopf_stueck():
    """Mittleres Knopfloch (START) aus der schrägen Knopfleiste des Pults."""
    (y0, z0), (y1, z1) = P.PULT_PROFIL[1], P.PULT_PROFIL[2]
    b = P.KNOPF_ABSTAND / 2 + 2
    return _ausschnitt(PU.gehaeuse(), -b, b, y0 - 1, y1 + 1, z0 - 12, z1 + 4)


def kabelkanal_stueck():
    """40 mm vom äußeren Kabelkanal: passen USB, 5 V und 19 V hinein, rastet die Lippe?"""
    return M.kabelkanal() & quader(-2000, 2000, -2000, 2000, 0, 40)


LOGO_TEST_D = 50


def logo_gravur(d=LOGO_TEST_D):
    """Runde Scheibe in Deckeldicke mit dem gravierten Logo, wie der Deckel kopfüber in Drucklage."""
    import schilder
    t = P.DECKEL_DICKE
    form = Pos(0, 0, t / 2) * Cylinder(d / 2 + 4, t)
    for f in schilder.logo_flaechen(d):
        form -= Pos(0, 0, t - P.DECKEL_GRAVUR) * extrude(f, amount=P.DECKEL_GRAVUR + 1, dir=(0, 0, 1))
    return Pos(0, 0, t) * Rot(180, 0, 0) * form


def pruefteile():
    """(Dateiname, Form, Anzahl, was prüfen)"""
    links, rechts = schwalben_fuge()
    return [
        ("1_Sensor_Tasche", sensor_tasche(), 1,
         "Sensor einlegen: sitzt er stramm und bündig, steckt die LED im Loch, ist das Lichtloch frei, passt die "
         f"Schraube {P.SCHRAUBE_SENSOR[0]}×{P.SCHRAUBE_SENSOR[1]}? Übersprechen später mit dem ganzen Testblock "
         "(ausgabe/druck/Prototyp_Testblock.stl)."),
        ("2_Huelsen_Ecke", huelsen_ecke(), 1,
         f"Alu-Rohr {P.PFOSTEN}×{P.PFOSTEN} einstecken: leicht saugend, nicht wackelig. "
         "Passt eine Sensorader durch den Schlitz unten in der Hülse?"),
        ("3_Schwalbe_links", links, 1,
         "Mit 3_Schwalbe_rechts zusammenstecken: geht mit Daumendruck, ohne Spalt (wird später verklebt)."),
        ("3_Schwalbe_rechts", rechts, 1, "siehe 3_Schwalbe_links"),
        ("4_Knopf_Stueck", knopf_stueck(), 1,
         f"Arcade-Knopf einschrauben (Loch {P.KNOPF_LOCH} mm). Unter der Platte messen: ist Knopf + "
         f"Mikroschalter höchstens {P.KNOPF_TIEFE} mm tief?"),
        ("5_Kabelkanal_Stueck", kabelkanal_stueck(), 1,
         "USB-Kabel, 5-V-Kabel und 19-V-Kabel einlegen: passen alle drei, halten die Rastlippen sie fest?"),
        ("6_Nest_Teil1_Wagos", M.nest_teile()[0], 1,
         "Endteil (später 2× gebraucht). Wago 221-415 einlegen: liegen sie ohne Klemmen in den Taschen, "
         "kommt man an die Einlässe und Hebel?"),
        ("6_Nest_Teil2_Board", M.nest_teile()[1], 1,
         "Endteil (später 2× gebraucht). Breakout-Board mit Pico und Wagos einlegen: passt alles, "
         "lassen sich beide Nest-Teile am Schwalbenschwanz zusammenstecken (später verkleben)?"),
        ("7_Logo_Gravur", logo_gravur(), 1,
         f"Logo-Gravur des Deckels, verkleinert auf Ø {LOGO_TEST_D} mm (Deckel: Ø {P.DECKEL_LOGO_D}). Liegt kopfüber: "
         f"bis {P.DECKEL_GRAVUR} mm schwarz, dann Filamentwechsel auf Weiß. Sind die weißen Linien sauber und "
         "geschlossen, deckt Weiß über Schwarz?"),
    ]
