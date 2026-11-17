"""
Exportiert das Modell in Baustufen und Einzelansichten für Blender:  python stufen.py
Jede Stufe wird eine eigene .glb in ausgabe/stufen/ (ein Objekt pro Teil, mit Namen und Farbe).
In Blender lädt `blender_laden.py` alle Dateien und beschriftet sie.

1–7 bilden zusammen die Kiste. 8–11 stehen rechts daneben und werden aus denselben
Funktionen erzeugt – jede Änderung in parameter.py/modell.py landet automatisch auch dort.
"""
import copy
from pathlib import Path

from build123d import Compound, Pos, export_gltf

import elektronik as E
import pult as PU
import modell as M
import parameter as P

ZIEL = Path(__file__).parent / "ausgabe" / "stufen"
ZIEL.mkdir(parents=True, exist_ok=True)

# Abstand der Einzelansichten nebeneinander (wächst mit der Kiste mit)
ABSTAND = M.AUSSEN_W + 300


def _kopie(t, label=None, versatz=(0, 0, 0)):
    # echte Kopie: sonst fasst der glTF-Export gleiche Formen zusammen und gibt
    # z. B. oberer und unterer Platte denselben Namen
    k = Pos(*versatz) * copy.deepcopy(t)
    k.label, k.color = label or t.label, t.color
    return k


def _auswahl(teile, praefixe, versatz=(0, 0, 0), kennung=""):
    return [_kopie(t, f"{kennung}{t.label}", versatz) for t in teile if t.label.startswith(praefixe)]


def _druckteile_flach(versatz):
    """Druckteile so, wie sie auf dem Druckbett liegen, leicht auseinandergezogen."""
    x0, y0, _ = versatz
    teile = []
    for i, s in enumerate(M.zerteilen(M.sensorplatte()), 1):
        s = M.teil(s, f"[10] Sensorplatte Teil {i} (2x drucken)", ("druck", "druck_c")[i % 2])
        teile.append(_kopie(s, versatz=(x0 + (i - 1.5) * 40, y0, 0)))
    tb = M.teil(M.testblock(), "[10] Prototyp-Testblock (2x drucken)", "druck")
    teile.append(_kopie(tb, versatz=(x0, y0 - 80, 0)))
    nest = M.teil(M.elektronik_nest(), "[10] Elektronik-Nest (2x drucken)", "druck_c")
    teile.append(_kopie(nest, versatz=(x0, y0 + 220, 0)))
    for i, d in enumerate(M.deckel_druck(), 1):
        d = M.teil(d, f"[10] Deckel Teil {i} (2x drucken)", "deckel")
        teile.append(_kopie(d, versatz=(x0 + (i - 1.5) * 40, y0 + 330, 0)))
    teile.append(_kopie(M.teil(PU.gehaeuse(), "[10] Pult Gehäuse (1x, mit Stützen)", "deckel"),
                        versatz=(x0 + 280, y0, 0)))
    teile.append(_kopie(M.teil(PU.boden(), "[10] Pult Boden (1x)", "druck"), versatz=(x0 + 280, y0 + 230, 0)))
    return teile


ELEKTRONIK = ("Elektronik-Nest", "Schraubklemmen", "Raspberry", "Wago", "Ader", "Zuleitung", "USB", "5-V",
              "19-V", "Kabelkanal")


def stufen():
    rahmen = M.rahmen()
    kaefig = rahmen + E.schrauben() + E.elektronik()
    return {
        "1_Rahmen": _auswahl(rahmen, ("Brett", "Seitenbrett")),
        "2_Lichtsensoren": _auswahl(rahmen, ("Sender", "Empfänger", "IR-Strahl")),
        "3_Sensorkaefig": _auswahl(rahmen, ("Sensorplatte", "Pfosten")),
        "4_Schrauben": _auswahl(kaefig, ("Schraube",)),
        "5_Elektronik_und_Kabel": _auswahl(kaefig, ELEKTRONIK),
        "6_LEDs_und_Deckel": _auswahl(rahmen, ("LED-", "Deckel")),
        "7_Bedienpult": _auswahl(PU.pult_teile(), ("",)),
        "8_Gitter_ohne_Pfosten": _auswahl(rahmen, ("Sensorplatte",), (ABSTAND, 0, 0), "[8] "),
        "9_Kaefig_mit_Sensoren_und_Kabeln": _auswahl(
            kaefig, ("Sensorplatte", "Pfosten", "Sender", "Empfänger", "IR-Strahl", "Schraube Sensor",
                     "Schraube Gitter", "Schraube Nest") + ELEKTRONIK, (2 * ABSTAND, 0, 0), "[9] "),
        "10_Druckteile_flach": _druckteile_flach((3 * ABSTAND, 0, 0)),
        # unteres Nest mit Pico, Wagos und den Adern-Enden, frei daneben
        "11_Elektronik_Nest": _auswahl(E.nest_teile(False) + E.adern(), ("Elektronik-Nest unten", "Schraubklemmen",
                                                                        "Raspberry", "Wago",
                                                                        "Ader rot Empf", "Ader schwarz Empf",
                                                                        "Ader gelb Empf"),
                                       (4 * ABSTAND, 0, -M.T), "[11] "),
    }


def export_stufen():
    for alt in ZIEL.glob("*.glb"):          # entfernte Stufen sollen auch in Blender verschwinden
        alt.unlink()
    for name, teile in stufen().items():
        # gleiche Namen durchnummerieren, damit Blender sie sauber auseinanderhält
        anzahl = {}
        for t in teile:
            anzahl[t.label] = anzahl.get(t.label, 0) + 1
        zaehler = {}
        for t in teile:
            if anzahl[t.label] > 1:
                n = zaehler[t.label] = zaehler.get(t.label, 0) + 1
                t.label = f"{t.label} {n:02d}"
        datei = ZIEL / f"{name}.glb"
        export_gltf(Compound(children=teile, label=name), str(datei), binary=True,
                    linear_deflection=0.2, angular_deflection=0.2)
        print(f"{name}: {len(teile)} Teile -> {datei}")


if __name__ == "__main__":
    export_stufen()
