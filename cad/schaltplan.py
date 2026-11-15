"""Erzeugt den KiCad-Schaltplan aus ausgabe/pins.json.

Aufruf: python schaltplan.py  ->  ausgabe/schaltplan/Schlagmesser.kicad_sch (+ .kicad_pro)
Prüfen:  kicad-cli sch erc ausgabe/schaltplan/Schlagmesser.kicad_sch
"""
import json
import uuid
from pathlib import Path

ORDNER = Path(__file__).resolve().parent / "ausgabe"
ZIEL = ORDNER / "schaltplan"
NAME = "Schlagmesser"
BIB = "DragonFist"
R = 2.54                      # Raster
STUB = 2 * R
_n = 0


def uid():
    global _n
    _n += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"dragonfist/{_n}"))


ROOT = uid()
FONT = "(effects (font (size 1.27 1.27)))"


def q(s):
    return '"' + str(s).replace('"', "'") + '"'


class Bauteil:
    """Kasten mit Pins links und rechts. Pin = (Nummer, Name, Typ)."""

    def __init__(self, name, links, rechts, breite):
        self.name, self.links, self.rechts, self.b = name, links, rechts, breite
        n = max(len(links), len(rechts))
        self.oben = (n // 2 + 1) * R
        self.unten = -(n - n // 2) * R

    def pins(self):
        for seite, liste in ((-1, self.links), (1, self.rechts)):
            k = len(liste) // 2
            for i, (nr, name, typ) in enumerate(liste):
                yield nr, name, typ, seite * (self.b / 2 + R), (k - i) * R, 0 if seite < 0 else 180

    def lib(self, praefix=BIB + ":"):
        pins = "".join(
            f'(pin {typ} line (at {x:.2f} {y:.2f} {w}) (length {R}) (name {q(name)} {FONT}) (number {q(nr)} {FONT}))'
            for nr, name, typ, x, y, w in self.pins())
        return (f'(symbol {q(praefix + self.name)} (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) '
                f'(on_board yes) (property "Reference" "X" (at 0 {self.oben + 1.27:.2f} 0) {FONT}) '
                f'(property "Value" {q(self.name)} (at 0 {self.unten - 1.27:.2f} 0) {FONT}) '
                f'(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))) '
                f'(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))) '
                f'(symbol "{self.name}_0_1" (rectangle (start {-self.b / 2:.2f} {self.oben:.2f}) '
                f'(end {self.b / 2:.2f} {self.unten:.2f}) (stroke (width 0.254) (type default)) (fill (type background)))) '
                f'(symbol "{self.name}_1_1" {pins}))')


class Plan:
    def __init__(self):
        self.teile, self.s = {}, []

    def typ(self, name, links, rechts, breite=15.24):
        self.teile[name] = Bauteil(name, links, rechts, breite)

    def setze(self, typ, ref, wert, x, y, netze, frei=()):
        """netze: Pin-Nummer -> Netzname. Pins in `frei` bekommen ein Nicht-verbunden-Kreuz."""
        t = self.teile[typ]
        pins = "".join(f'(pin {q(nr)} (uuid "{uid()}"))' for nr, *_ in t.pins())
        self.s.append(
            f'(symbol (lib_id {q(BIB + ":" + typ)}) (at {x:.2f} {y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom yes) '
            f'(on_board yes) (dnp no) (uuid "{uid()}") '
            f'(property "Reference" {q(ref)} (at {x:.2f} {y - t.oben - 1.27:.2f} 0) {FONT}) '
            f'(property "Value" {q(wert)} (at {x:.2f} {y - t.unten + 1.9:.2f} 0) {FONT}) '
            f'(property "Footprint" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes))) '
            f'(property "Datasheet" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes))) '
            f'{pins} (instances (project {q(NAME)} (path "/{ROOT}" (reference {q(ref)}) (unit 1)))))')
        for nr, _, _, px, py, w in t.pins():
            ex, ey = x + px, y - py
            if nr in frei:
                self.s.append(f'(no_connect (at {ex:.2f} {ey:.2f}) (uuid "{uid()}"))')
                continue
            zx = ex + (-STUB if w == 0 else STUB)
            self.s.append(f'(wire (pts (xy {ex:.2f} {ey:.2f}) (xy {zx:.2f} {ey:.2f})) (stroke (width 0) (type default)) '
                          f'(uuid "{uid()}"))')
            self.s.append(f'(label {q(netze[nr])} (at {zx:.2f} {ey:.2f} {180 if w == 0 else 0}) (effects (font (size 1.27 1.27)) '
                          f'(justify {"right" if w == 0 else "left"} bottom)) (uuid "{uid()}"))')

    def text(self, t, x, y, gr=1.8):
        t = t.replace("\n", "\\n")
        self.s.append(f'(text {q(t)} (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) (effects (font (size {gr} {gr})) '
                      f'(justify left bottom)) (uuid "{uid()}"))')

    def schreiben(self):
        lib = "".join(t.lib() for t in self.teile.values())
        kopf = (f'(kicad_sch (version 20231120) (generator "schaltplan_py") (generator_version "8.0") (uuid "{ROOT}") '
                f'(paper "A3") (title_block (title "DragonFist – Schlag-Messgerät") (rev "1") '
                f'(comment 1 "Automatisch erzeugt von schaltplan.py aus ausgabe/pins.json")) (lib_symbols {lib})')
        ZIEL.mkdir(parents=True, exist_ok=True)
        (ZIEL / f"{NAME}.kicad_sch").write_text(
            kopf + "\n" + "\n".join(self.s) + '\n(sheet_instances (path "/" (page "1"))))\n', encoding="utf-8")
        (ZIEL / f"{BIB}.kicad_sym").write_text(
            '(kicad_symbol_lib (version 20231120) (generator "schaltplan_py") (generator_version "8.0") '
            + "".join(t.lib("") for t in self.teile.values()) + ")\n", encoding="utf-8")
        (ZIEL / "sym-lib-table").write_text(
            f'(sym_lib_table (version 7) (lib (name "{BIB}") (type "KiCad") (uri "${{KIPRJMOD}}/{BIB}.kicad_sym") '
            '(options "") (descr "")))\n', encoding="utf-8")
        pro = ZIEL / f"{NAME}.kicad_pro"
        if not pro.exists():
            pro.write_text(json.dumps({"meta": {"filename": pro.name, "version": 1}}), encoding="utf-8")


def bauen():
    d = json.loads((ORDNER / "pins.json").read_text(encoding="utf-8"))
    sens = d["sensoren"]
    p = Plan()
    p.typ("Empfaenger", [], [("1", "+5V rot", "power_in"), ("2", "OUT weiß", "open_collector"),
                             ("3", "GND schwarz", "power_in")], 22.86)
    p.typ("Sender", [("1", "+5V rot", "power_in")], [("2", "GND schwarz", "power_in")], 22.86)
    p.typ("Netzteil_5V_4A", [], [("1", "+ (Mitte)", "power_out"), ("2", "−", "power_out")], 20.32)
    p.typ("Elko", [("1", "+ lang", "passive")], [("2", "− Streifen", "passive")], 25.4)
    p.typ("R", [("1", "~", "passive")], [("2", "~", "passive")], 7.62)
    p.typ("LED_Streifen", [("1", "+5V rot", "power_in"), ("2", "DIN", "input"), ("3", "GND", "power_in")], [], 22.86)

    netz = {s["nr"]: f'{s["ebene"]}{s["nr"] if s["ebene"] == "A" else s["nr"] - 6}_GP{s["gpio"]}' for s in sens}
    led = {k: f"LED_{k.upper()}_GP{g}" for k, g in d["gpio_led"].items()}
    li = [(str(s["pin"]), f'GP{s["gpio"]}', "bidirectional", netz[s["nr"]]) for s in sens if s["ebene"] == "A"]
    li.append(("21", "GP16", "bidirectional", led["links"]))
    re = [(str(s["pin"]), f'GP{s["gpio"]}', "bidirectional", netz[s["nr"]])
          for s in sorted((s for s in sens if s["ebene"] == "B"), key=lambda s: s["gpio"])]
    re.insert(2, ("25", "GP19", "bidirectional", led["rechts"]))
    re += [("3", "GND", "power_in", "GND"), ("40", "VBUS", "passive", ""), ("39", "VSYS", "passive", "")]
    p.typ("Pico_2", [x[:3] for x in li], [x[:3] for x in re], 27.94)

    p.text("DragonFist – Schlag-Messgerät: 13 IR-Lichtschranken (Adafruit 2168), Pico 2, 2 LED-Streifen", 25.4, 22.86, 3)
    p.text("Netze mit gleichem Namen sind verbunden. +5V und GND laufen über die Wago-Klemmen (unten und oben gebrückt).",
           25.4, 29.21)

    p.text("EMPFÄNGER EBENE A (unten)", 25.4, 43.18, 2.2)
    p.text("EMPFÄNGER EBENE B (unten)", 106.68, 43.18, 2.2)
    n = {"A": 0, "B": 0}
    for s in sens:
        e = s["ebene"]
        x, y = (40.64 if e == "A" else 121.92), 55.88 + n[e] * 17.78
        n[e] += 1
        nr = n[e]
        p.setze("Empfaenger", f"E{s['nr']}", f"{e}{nr}  {s['x_mm']:+d} mm", x, y,
                {"1": "+5V", "2": netz[s["nr"]], "3": "GND"})
    p.text("Ausgang Open-Collector: schaltet nur gegen GND.\nDie 3,3 V kommen vom internen Pull-up im Pico\n"
           "(Pin.PULL_UP), es liegen nie 5 V am GP-Pin.", 25.4, 190.5)

    p.text("PICO 2 (Schraubklemmen-Board)", 195.58, 43.18, 2.2)
    p.setze("Pico_2", "U1", "Raspberry Pi Pico 2 H", 218.44, 73.66, {x[0]: x[3] for x in li + re}, frei=("40", "39"))
    p.text("Strom nur über USB vom Jetson.\nVBUS und VSYS bleiben frei, sonst speisen\nUSB und Netzteil gegeneinander.",
           195.58, 106.68)

    p.text("LED-STREIFEN (WS2812B, je 19 LEDs)", 292.1, 43.18, 2.2)
    for k, (seite, y) in enumerate((("links", 58.42), ("rechts", 86.36))):
        dn = f"LED_{seite.upper()}_DIN"
        p.setze("R", f"R{k + 1}", "330 Ω", 304.8, y, {"1": led[seite], "2": dn})
        p.setze("LED_Streifen", f"LED{k + 1}", f"Streifen {seite}", 373.38, y, {"1": "+5V", "2": dn, "3": "GND"})
    p.text("330 Ω in jeder Datenleitung schützt den Pico,\nwenn die LEDs noch keinen Strom haben.\n"
           f"Firmware begrenzt die Helligkeit auf {d['led_helligkeit']:.0%}.", 292.1, 109.22)

    p.text("STROMVERSORGUNG", 195.58, 132.08, 2.2)
    p.setze("Netzteil_5V_4A", "J1", "MeanWell 5 V / 4 A über DC-Kupplung", 213.36, 147.32, {"1": "+5V", "2": "GND"})
    p.setze("Elko", "C1", "1000 µF / 16 V", 292.1, 147.32, {"1": "+5V", "2": "GND"})
    p.text("Vor dem ersten Einstecken Polung mit dem Multimeter prüfen.\nElko: langes Bein an +5V, Streifen an GND – "
           "falsch herum kann er platzen.\nBedarf: 13 Sender ca. 0,26 A + Empfänger ca. 0,1 A + LEDs ca. 0,8 A = ca. 1,2 A.",
           195.58, 170.18)

    p.text("SENDER (oben, Zuleitung +5V/GND durch den hinteren linken Alu-Pfosten)", 25.4, 208.28, 2.2)
    for k, s in enumerate(sens):
        e = s["ebene"]
        nr = s["nr"] if e == "A" else s["nr"] - 6
        p.setze("Sender", f"D{s['nr']}", f"Sender {e}{nr}", 48.26 + (k % 7) * 53.34, 222.25 + (k // 7) * 22.86,
                {"1": "+5V", "2": "GND"})
    p.text("Vorwiderstand ist im Sender eingebaut: direkt an 5 V, ca. 20 mA je Sender.", 25.4, 264.16)
    p.schreiben()


if __name__ == "__main__":
    bauen()
    print(ZIEL / f"{NAME}.kicad_sch")
