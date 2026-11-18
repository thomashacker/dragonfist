"""
Erzeugt alles neu:  python build.py

  ausgabe/Aufbau_Kinder.step, Aufbau_Erwachsene.step   -> in Fusion/FreeCAD/Onshape öffnen
  ausgabe/*.glb                                        -> Vorschau (Blender, Windows 3D-Viewer)
  ausgabe/druck/*.stl                                  -> für den Slicer
  ausgabe/Bericht.txt                                  -> Prüfungen, Zuschnitt- und Einkaufsliste
  Einkaufsliste.md                                     -> aktueller Stand zum Einkaufen
  ausgabe/stufen/*.glb                                 -> Blender (danach blender_laden.py ausführen)
"""
import math
from pathlib import Path

from build123d import Pos, export_gltf, export_step, export_stl

import elektronik as E
import modell as M
import parameter as P

AUS = Path(__file__).parent / "ausgabe"
DRUCK = AUS / "druck"
DRUCK.mkdir(parents=True, exist_ok=True)

bericht = []


def zeile(text=""):
    print(text)
    bericht.append(text)


def ok(bedingung):
    return "OK " if bedingung else "!! "


# ---------------------------------------------------------------------------
# Druckteile
# ---------------------------------------------------------------------------
druckteile = []
for f in DRUCK.glob("*.stl"):          # alte Stücke entfernen, falls sich die Teilung ändert
    f.unlink()
platte = M.zerteilen(M.sensorplatte())
druckteile += [(f"Sensorplatte_Teil{i}", s, 2) for i, s in enumerate(platte, 1)]
druckteile += [(f"Elektronik_Nest_Teil{i}", n, 2) for i, n in enumerate(M.nest_teile(), 1)]
druckteile += [(f"Deckel_Teil{i}", d, 2) for i, d in enumerate(M.deckel_druck(), 1)]
import pult as PU  # noqa: E402
druckteile += [("Pult_Gehaeuse", PU.gehaeuse(), 1), ("Pult_Boden", PU.boden(), 1)]
import schilder as SCH  # noqa: E402
druckteile += [(n, f, 1) for n, f in SCH.druckteile()]
druckteile += [(f"Kabelkanal_Teil{i}", Pos(0, 0, 0) * k, 1) for i, k in enumerate(M.kabelkanal_teile(), 1)]
druckteile.append(("Prototyp_Testblock", M.testblock(), 2))

zeile("=== Druckteile (flach auf dem Gitter drucken, Türmchen nach oben"
      + ("; Lippe braucht Stützen" if P.MIT_LIPPE else ", ohne Stützen") + ") ===")
gramm_gesamt = 0
for name, form, anzahl in druckteile:
    bb = form.bounding_box().size
    klein, gross = sorted((bb.X, bb.Y))
    passt = klein <= min(P.DRUCKBETT) and gross <= max(P.DRUCKBETT)
    gramm = form.volume / 1000 * 1.24 * 0.45     # PLA, grob mit 3 Wänden / 20 % Füllung
    gramm_gesamt += gramm * anzahl
    zeile(f"{ok(passt)}{name}: {bb.X:.0f} x {bb.Y:.0f} x {bb.Z:.0f} mm, {anzahl}x drucken, ca. {gramm:.0f} g")
    export_stl(form, str(DRUCK / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
zeile(f"   Filament gesamt ca. {gramm_gesamt:.0f} g")

# ---------------------------------------------------------------------------
# Prüfdruck: Ausschnitte der echten Teile, vor dem großen Druck mit den echten Bauteilen testen
# ---------------------------------------------------------------------------
import pruefteile as PT  # noqa: E402

PRUEF = AUS / "pruefdruck"
PRUEF.mkdir(exist_ok=True)
for f in PRUEF.glob("*.stl"):
    f.unlink()
zeile()
zeile("=== Prüfdruck (zuerst drucken) ===")
pruef_zeilen, pruef_gramm = [], 0
for name, form, anzahl, wozu in PT.pruefteile():
    bb = form.bounding_box().size
    gramm = form.volume / 1000 * 1.24 * 0.45
    pruef_gramm += gramm * anzahl
    export_stl(form, str(PRUEF / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
    zeile(f"   {name}: {bb.X:.0f} x {bb.Y:.0f} x {bb.Z:.0f} mm, {anzahl}x, ca. {gramm:.0f} g")
    pruef_zeilen.append(f"| `{name}.stl` | {anzahl}× | {bb.X:.0f} × {bb.Y:.0f} × {bb.Z:.0f} mm | {wozu} |")
zeile(f"   Prüfdruck gesamt ca. {pruef_gramm:.0f} g")
(Path(__file__).parent / "Pruefdruck.md").write_text(f"""# Prüfdruck – zuerst drucken, dann erst alles andere

*Automatisch erzeugt von `build.py`. Dateien: `ausgabe/pruefdruck/`. Zusammen ca. {pruef_gramm:.0f} g PLA oder PETG,
gleiche Einstellungen wie später für die Endteile (0,2 mm Schicht, 3 Wände, 20 % Füllung, ohne Stützen).*

Jedes Stück ist ein Ausschnitt aus dem echten Teil – gleiche Maße, gleiche Passungen.
Passt ein Stück nicht: messen, Wert in `parameter.py` ändern (Zeilen mit `# MESSEN`), `python build.py`, neu drucken.

| Datei | Anzahl | Größe | Was prüfen |
|---|---|---|---|
{chr(10).join(pruef_zeilen)}

## Reihenfolge
1. Sensoren (Adafruit) messen: Gehäuse, LED-Kuppe, Befestigungsloch → `parameter.py` → neu bauen → **dann** drucken.
2. Prüfteile drucken, mit den echten Teilen testen, Maße anpassen.
3. Display, Jetson-Lochabstand, Boxenflansch nachmessen (stehen ebenfalls mit `# MESSEN` in `parameter.py`).
4. Erst dann die Endteile aus `ausgabe/druck/` drucken (ca. {gramm_gesamt:.0f} g).
""", encoding="utf-8")

# ---------------------------------------------------------------------------
# Aufbauten
# ---------------------------------------------------------------------------
kind, k_info = M.aufbau_kinder()
erw, e_info = M.aufbau_erwachsene()
for name, comp in (("Aufbau_Kinder", kind), ("Aufbau_Erwachsene", erw)):
    export_step(comp, str(AUS / f"{name}.step"))
    export_gltf(comp, str(AUS / f"{name}.glb"), binary=True, linear_deflection=0.5, angular_deflection=0.3)

# ---------------------------------------------------------------------------
# Prüfungen
# ---------------------------------------------------------------------------
zeile()
zeile("=== Maße ===")
zeile(f"   Rahmen außen: {M.AUSSEN_W:.0f} breit x {M.AUSSEN_H:.0f} hoch x {M.TIEFE:.0f} tief "
      )
zeile(f"   Türmchen hoch: {M.LEISTE_DICKE:.1f} mm, lichte Fensterhöhe {P.FENSTER_HOEHE:.1f} mm")
zeile(f"   Ebene A bei {M.Y_A} mm, B bei {M.Y_B} mm (ab Rahmenvorderkante)")
zeile(f"   1 mm Fehler im Ebenenabstand = {100 / P.EBENENABSTAND_AB:.1f} % Geschwindigkeitsfehler")

zeile()
zeile("=== Strahlen ===")
strecke = P.FENSTER_HOEHE + 2 * P.TUNNEL_LAENGE
zeile(f"{ok(strecke < 450)}Strahllänge LED zu LED ca. {strecke:.0f} mm (Reichweite 5-mm-Version ca. 500 mm)")
tunnel = math.degrees(math.atan(P.TUNNEL_DURCHMESSER / P.TUNNEL_LAENGE))
for name, xs in (("A", P.STRAHLEN_A), ("B", P.STRAHLEN_B)):
    if len(xs) < 2:
        continue
    xs = sorted(xs)
    abst = min(b - a for a, b in zip(xs, xs[1:]))
    nachbar = math.degrees(math.atan(abst / strecke))
    if name == "A":                      # Schaumstoff-Trennung in der Mitte zählt als Rand
        h = P.TRENNUNG_A_BREITE / 2
        xs = sorted(xs + [-h, h])
    luecken = [b - a for a, b in zip(xs, xs[1:])] + [xs[0] + P.FENSTER_BREITE / 2,
                                                       P.FENSTER_BREITE / 2 - xs[-1]]
    if name == "A":
        luecken = [l for l in luecken if l != P.TRENNUNG_A_BREITE]
        xs = [x for x in xs if abs(x) != h]
    zeile(f"{ok(tunnel < nachbar * 0.9)}Ebene {name}: Nachbarstrahl unter {nachbar:.1f}°, "
          f"Tunnel lässt ca. {tunnel:.1f}° durch; größte Lücke {max(luecken):.0f} mm")
for x in P.STRAHLEN_A + P.STRAHLEN_B:
    for t in P.LEISTE_TEILUNGEN:
        if abs(x - t) < M.TURM_X / 2 + 1:
            zeile(f"!! Türmchen bei x={x} liegt auf der Trennfuge x={t}")
n_strahlen = len(P.STRAHLEN_A) + len(P.STRAHLEN_B)
n_led = len(P.GPIO_LED)
zeile(f"{ok(n_strahlen + n_led <= P.GPIO_FREI)}{n_strahlen} Sensorpaare + {n_led} LED-Pins = {n_strahlen + n_led} "
      f"von {P.GPIO_FREI} GPIOs am Pico")

zeile()
zeile("=== Höhen / Stativ ===")
for titel, info in (("Kinder", k_info), ("Erwachsene", e_info)):
    kopf = info["stativkopf"]
    zeile(f"{ok(P.STATIV_MIN <= kopf <= P.STATIV_MAX)}{titel}: Stativkopf auf {kopf:.0f} mm "
          f"(Stativ {P.STATIV_MIN}–{P.STATIV_MAX})")
mitte = M.fenster_mitte_im_rahmen()
f_min = P.STATIV_MIN + P.FLANSCH_PLATTE[2] + mitte
f_max = P.STATIV_MAX + P.FLANSCH_PLATTE[2] + mitte
zeile(f"   Fenstermitte mit diesem Stativ einstellbar: {f_min:.0f}–{f_max:.0f} mm")

# ---------------------------------------------------------------------------
# Zuschnitt und Einkauf
# ---------------------------------------------------------------------------
T = P.BRETT_DICKE
zeile()
zeile(f"=== Zuschnitt (Leimholz Kiefer {T} mm, im Baumarkt sägen lassen) ===")
zeile(f"   4x  Brett (oben, unten, Seiten) {P.BRETT[0]} x {P.BRETT[1]}")

zeile()
zeile("=== Elektronik ===")
weg = E.kabellaenge_max()
kurz = E.zu_kurz()
zeile(f"{ok(not kurz)}Längster Adernweg Sensor -> Nest ca. {weg:.0f} mm, Sensorkabel {P.SENSORKABEL} mm, "
      f"Reserve {E.RESERVE} mm" + (f": {len(kurz)} Adern brauchen eine Verlängerung" if kurz else ""))
for name, laenge in kurz:
    zeile(f"      {name}: {laenge:.0f} mm")
zeile(f"{ok(not E.ENGSTELLEN)}Kabelführung: {len(E.adern_wege())} Leitungen, "
      f"{len(E.ENGSTELLEN)} berühren eine andere")
wb = E.wago_bedarf()
for platte in ("unten", "oben"):
    zeile(f"   Wago {platte}: 5V {E._wago_text(platte, '5V')}, GND {E._wago_text(platte, 'GND')}")
zeile(f"   Wago 221-415 gesamt: {wb['gesamt']}")
zeile(f"   Kabelaustritt hinten links bei x={M.austritt_x():.0f} mm")
for art, n in E.schrauben_anzahl().items():
    zeile(f"   {art}: {n}")

(AUS / "Bericht.txt").write_text("\n".join(bericht), encoding="utf-8")
(Path(__file__).parent / "Verkabelung.md").write_text(E.verkabelung_md(), encoding="utf-8")
(AUS / "Verkabelung.svg").write_text(E.verkabelung_svg(), encoding="utf-8")
(AUS / "pins.json").write_text(E.pins_json(), encoding="utf-8")

# ---------------------------------------------------------------------------
# Einkaufsliste (wird bei jedem Lauf aus den Parametern neu geschrieben)
# ---------------------------------------------------------------------------
n_platte = len(M.zerteilen(M.sensorplatte()))

# Wie viele Leimholzplatten (HOLZ_PLATTE) braucht der Zuschnitt? (einfaches Einsortieren, 4 mm Sägeschnitt)
HOLZ_PLATTE = (2000, 300)
reste = []
for stueck in sorted([M.AUSSEN_H, M.AUSSEN_H, P.FENSTER_BREITE, P.FENSTER_BREITE], reverse=True):
    for i, rest in enumerate(reste):
        if rest >= stueck + 4:
            reste[i] -= stueck + 4
            break
    else:
        reste.append(HOLZ_PLATTE[0] - stueck - 4)
n_holz = len(reste)
if M.TIEFE > HOLZ_PLATTE[1]:
    zeile(f"!! Brett-Tiefe {M.TIEFE:.0f} mm ist breiter als die Leimholzplatte ({HOLZ_PLATTE[1]} mm)")
schr = E.schrauben_anzahl()
import json  # noqa: E402

try:
    bestellt = json.loads((Path(__file__).parent / "bestellt.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    bestellt = {}


def _symbol(status):
    return "✅" if status.startswith("geliefert") else "🚚"


def haken(schluessel):
    """✅ geliefert / 🚚 bestellt oder unterwegs / ⬜ noch kaufen – laut bestellt.json."""
    for b in bestellt.values():
        if schluessel in b.get("haken", []):
            return f"{_symbol(b['status'])} **{b['status']}** – "
    return "⬜ "


def offen(schluessel):
    return haken(schluessel) == "⬜ "


bestellstand = "\n".join(f"| {_symbol(b['status'])} {wo} | {b['inhalt']} | {b['datum']} | {b['preis']} | {b['status']} |"
                          for wo, b in bestellt.items()) or "| – | | | | |"
einkauf = f"""# Einkaufsliste – Schlag-Messgerät (Stand: Rahmen, Sensorkäfig, Elektronik)

*Automatisch erzeugt von `build.py` – nicht von Hand ändern. Abhaken: Eintrag in `bestellt.json`.*

## Bestellstand
| Wo | Inhalt | Datum | Preis | Status |
|---|---|---|---|---|
{bestellstand}

## Elektronik
| Teil | Menge | ca. Preis | Link |
|---|---|---|---|
| {haken('lichtschranken')}IR-Lichtschranke **Adafruit 2168** (5 mm, 50 cm, Sender + Empfänger) – **nicht 2167 (3 mm)** | {n_strahlen} + 2 Reserve | 5,36 $ / Paar ab 10 = {(n_strahlen + 2) * 5.36:.0f} $ + Versand + 19 % EUSt | [Adafruit](https://www.adafruit.com/product/2168) (USA, 1–2 Wochen) |
| … oder aus der EU{' (entfällt, schon bestellt)' if not offen('lichtschranken') else ''} | | 6,95 € / Paar | [elektronicavoorjou.nl](https://elektronicavoorjou.nl/en/product/IR-break-beam-sensor-5mm-LEDs) (NL, ab 99,95 € versandfrei) |
| {haken('pico')}Raspberry Pi Pico 2 **H** (Stiftleisten schon dran) – einer reicht für alles | 1 (+1 Reserve, optional) | 6,50 € | [BerryBase](https://www.berrybase.de/raspberry-pi-pico-2-rp2350-mikrocontroller-board-mit-headern) |
| {haken('usb')}Micro-USB-Kabel **mit Datenleitung** (kein reines Ladekabel), ca. 1–2 m – Pico an PC/Jetson | 1 | 4 € | beliebig |
| {haken('breakout')}Schraubklemmen-Board für den Pico | 1 | 4,90 € | [BerryBase](https://www.berrybase.de/en/breakout-board-mit-schraubklemmen-und-buchsenleisten-fuer-raspberrry-pi-pico) |
| {haken('netzteil')}Netzteil 5 V / 4 A, Hohlstecker 5,5×2,1 (reicht später auch für die LEDs) | 1 | 15 € | [BerryBase](https://www.berrybase.de/meanwell-schaltnetzteil-5v-dc-4-0a-mit-hohlstecker-5-5x2-1mm) |
| {haken('dc')}DC-Kupplung 5,5×2,1 mm mit Schraubklemmen (goobay 76743), + / − beschriftet; mit 2 Stück Litze an die Wago | 1 | 0,60 € | BerryBase, Art.-Nr. 76743 |
| {haken('wago')}Wago 221-415 (5 Leiter) | {wb['gesamt']} → 25er-Pack | 13 € | [elektrikshop.de](https://www.elektrikshop.de/25-stk-compact-5-leiter-klemmen-mit-bet-hebel-221-415-wago.html) |
| {haken('amazon_draht')}Draht 20 AWG (≈ 0,5 mm²) rot, schwarz, gelb – z. B. TUOFENG-Set Massivdraht (Pfosten-Zuleitung, DC-Kupplung, LEDs) | je ca. 2 m | 19 € (Set) | Amazon |

Tipp: alle Sensoren auf einmal bestellen – dann ist der Versand frei und der Prototyp nutzt schon die echten Teile.
Die Sensorkabel reichen bis zum Pico, **keine Verlängerung nötig**. Wie alles verbunden wird: `Verkabelung.md`.

## LEDs
| Teil | Menge | ca. Preis | Link |
|---|---|---|---|
| {haken('amazon')}WS2812B-LED-Streifen 5 V, {P.LED_PRO_M} LEDs/m, **10 mm breit**, IP30 (z. B. LOAMLIN 5 m, schwarze Platine) – klebt auf den vorderen Alu-Pfosten | 1 → 2× {M.led_anzahl()} LEDs | 23 € (5 m) | Amazon |
| {haken('amazon')}Lötfreie LED-Verbinder **3pin, 10 mm, SMD** (BTF-LIGHTING Transparent Connector Kit, 12 Stück + 4 Kabel) – je Streifen einer, Draht 20 AWG direkt einklemmen | 1 Set | 9 € | Amazon („BTF-LIGHTING 3pin SMD 10mm Transparent Connector Kit“) |
| {haken('amazon')}Widerstand 330 Ω, 1/4 W (in jede LED-Datenleitung; Farbringe orange-orange-braun-gold) – z. B. ONJYHK-Sortiment 1000 Stück, enthält 10× 330 Ω | 2 (+ Reserve) | ca. 10 € (Set) | Amazon |
| {haken('amazon')}Elko 1000 µF **16 V** (am Netzteil-Eingang, Polung: Streifen = −) – ALLECIN 15er-Pack | 1 | 7 € | Amazon |
| {haken('amazon_wago412')}Wago 221-412 (2 Leiter, Widerstand ↔ Datenader) | 2 → 16er-Pack | 6 € | Amazon (verkauft von Amazon) |
| {haken('amazon')}Pegelwandler 3,3 → 5 V SN74AHCT125**N** (DIP-14, steckt ins Breadboard) | 1 (10er-Pack) | 10 € | Amazon – **optional, nur falls die LEDs flackern** |

Strom: max. {E.led_strom_a():.1f} A, Firmware begrenzt auf {P.LED_HELLIGKEIT:.0%} → ca. {E.led_strom_a() * P.LED_HELLIGKEIT:.1f} A. Das {P.NETZTEIL_A:.0f}-A-Netzteil reicht.

## Bedienpult (oben auf der Kiste)
| Teil | Menge | ca. Preis | Link |
|---|---|---|---|
| {haken('amazon')}7"-HDMI-Display ELECROW 1024×600, Touch, USB-Strom (Maß im Modell {P.DISPLAY[0]}×{P.DISPLAY[1]} mm – nachmessen) | 1 | 47 € | Amazon |
| {haken('amazon')}Kabel DisplayPort → HDMI, 0,9 m (Amazon Basics, Jetson hat nur DisplayPort) | 1 | 9 € | Amazon |
| {haken('amazon')}USB-Hub 4 Port (Sabrent HB-UM43) – Display + Pico direkt an den Jetson, Encoder + Lautsprecher an den Hub | 1 | 9 € | Amazon |
| {haken('amazon')}Arcade-Knöpfe 30 mm + **USB-Encoder** (Set, lötfrei, Steckkabel) – {len(P.KNOEPFE)} Knöpfe: {", ".join(P.KNOEPFE)}, dazu der Joystick aus dem Set | 1 Set | 25 € | Amazon: EG STARTS USB-Encoder + Joystick + 10 LED-Knöpfe 5 V (Joystick bleibt übrig) |
| {haken('amazon')}USB-Lautsprecher HuaLiSiJi 3 W ({P.LAUTSPRECHER[0]}×{P.LAUTSPRECHER[1]}×{P.LAUTSPRECHER[2]} mm, eigene USB-Soundkarte) – steht **außen** rechts neben dem Pult, 2 Schrauben 2,5×16 durch die Ösen ins Brett | 1 | 17 € | Amazon |
| {haken('amazon')}Schrauben M3×10 (Gehäuse an Boden) + M2.5×6 (Jetson) | 4 + 4 | 3 € | Baumarkt |
| ✅ Jetson **Orin** Nano Developer Kit (P3766 geprüft) | vorhanden | – | – |
| {haken('jetson_netzteil')}Netzteil für den Jetson Orin Nano: **19 V**, ≥ 2,4 A (65-W-Laptopnetzteil 19 V / 3,42 A passt), Hohlstecker **5,5 × 2,5 mm**, **Mitte = Plus** – passt zum vorhandenen Orin Nano (P3766) | 1 | ca. 15–20 € | noch kaufen |
| {haken('jetson_sd')}microSD-Karte für den Jetson: **mind. 64 GB, besser 128 GB, UHS-I U3 / A2** (z. B. SanDisk Extreme oder Samsung PRO Plus) – Markenkarte, keine No-Name | 1 | ca. 15–20 € | Elektronikmarkt / Amazon |

Das Pult-Gehäuse ist {P.PULT_BREITE}×{P.PULT_TIEFE}×{max(z for _, z in P.PULT_PROFIL)} mm (Drucker mit mind. 180 mm Bauhöhe, Knopfleiste mit Stützen).
Kabel außen: USB (Pico → Jetson), 5 V (Netzteil → Kiste) und 19 V (Jetson-Netzteil) laufen im **gedruckten Kabelkanal** hinten am linken Seitenbrett (2 Teile, Rastlippe). Vom Boden bis zur Kiste: Netzkabel mit **Klett-Kabelbindern** am Stativrohr (1 Pack, ca. 4 €, Baumarkt).

## Sensorkäfig
| Teil | Menge | ca. Preis | Link |
|---|---|---|---|
| {haken('alurohr')}Alu-Vierkant**rohr** {P.PFOSTEN}×{P.PFOSTEN}×1 mm (Kaiserthal), 1 m → je Stange 2× {M.pfosten_laenge():.0f} mm, ergibt {len(M.pfosten_xy())} Pfosten | {-(-len(M.pfosten_xy()) // (1000 // (M.pfosten_laenge() + 2)) ):.0f} Stangen | 3,75 € / Stange | Hornbach Art.-Nr. 6368969 (Berlin-Weißensee, im Markt abholen) |
| {haken('amazon')}Halbrundschraube {P.SCHRAUBE_GITTER[0]}×{P.SCHRAUBE_GITTER[1]} (Gitter, Nest, Kabelkanal ans Holz) | {schr['Schraube Gitter'] + schr['Schraube Nest'] + schr['Schraube Kabelkanal']} | – | Baumarkt |
| {haken('amazon_schraube25')}Holzschraube {P.SCHRAUBE_SENSOR[0]}×{P.SCHRAUBE_SENSOR[1]} **Halbrund-/Linsenkopf**, kein Senkkopf (Sensoren + Deckel, ins Holz) | {schr['Schraube Sensor'] + schr['Schraube Deckel']} + Reserve | 6,63 € (50 Stück) | [Amazon: DIN 96 Edelstahl 2,5×16](https://www.amazon.de/dp/B0F1YF4CH5) |
| {haken('amazon')}Sekundenkleber (die zwei Hälften jeder Sensorplatte am Schwalbenschwanz verkleben) | 1 | 3 € | Baumarkt |
| {haken('drucker')}Filament PLA 1,75 mm – **schwarz** für Sensorplatten/Testblock (IR-dicht), **weiß** für Pult, Deckel, Kabelkanal, Nest (Sensorplatte {n_platte} Teile je 2×, Deckel {n_platte} Teile je 2×, Nest 2×, Testblock 2×) | ca. {gramm_gesamt:.0f} g | 20 € / Rolle | beliebig |

## Holz (Leimholz Kiefer {T} mm, im Baumarkt zuschneiden lassen)
| Teil | Menge | Maß | Link |
|---|---|---|---|
| ✅ **gekauft (14.11.)** – Bretter Leimholz {T} mm, fertig zugeschnitten (oben, unten, links, rechts + 1 Reserve für Probeanstrich/Pult) | 5 | {P.BRETT[0]} × {P.BRETT[1]} mm | Baumarkt |
| ✅ **gekauft (14.11.)** – Acryl-Buntlack schwarz seidenmatt 750 ml (ganze Kiste, Rest für Pult) · Schleifpapier 120 + 180 · Malerset (Pinsel, Rolle, Krepp) | 1 | – | Baumarkt |
| {haken('amazon')}Holzschraube {P.SCHRAUBE_RAHMEN[0]}×{P.SCHRAUBE_RAHMEN[1]} (Seitenbrett in Brett oben/unten) | {schr['Schraube Rahmen']} | – | Baumarkt |
| {haken('amazon')}Holzleim (Ecken zusätzlich verleimen) | 1 | 4 € | Baumarkt |

## Werkzeug
| Teil | Link |
|---|---|
| {haken('amazon')}Metallsäge (Presch Junior) + Schneidlade kwb (Alu-Rohr gerade absägen) | Amazon |
| {haken('amazon')}Abisolierzange automatisch + Seitenschneider VCELINK | Amazon |
| {haken('amazon')}Messschieber Spurtar · Multimeter AstroAI (Polung prüfen!) | Amazon |
| ⬜ Metallfeile (Alu-Schnittkanten entgraten) | Baumarkt |
| ✅ Schleifpapier 120 · Unterlegscheiben M5 (4 Stück, Flansch) · Schlitz-Schraubendreher | vorhanden |
| ✅ Akkuschrauber mit Torx-Bit T20 | vorhanden |

## Kabelordnung und Aufbewahrung
| Teil | Link |
|---|---|
| {haken('amazon')}Kabelschlauch 13 mm, 3 m (Strom/USB am Stativ) · Kabelclips selbstklebend · Kabelbinder 100 mm + Klett | Amazon |
| {haken('amazon')}Kabeletiketten (Sensoren A1–A6, B1–B7 beschriften) | Amazon |
| {haken('amazon')}ESD-Beutel · Sortimentskasten Stanley 30 Schubladen | Amazon |

*Preise: Stand der Recherche, können sich ändern.*

## Aufbau (Stativ)
| Teil | Menge | ca. Preis | Link |
|---|---|---|---|
| {haken('amazon_stativ')}Lautsprecherstativ **niedrig**, Stahl, 35-mm-Flansch, 67–120 cm, bis 50 kg (Pronomic SPS-5S) – ein Stativ für Kinder **und** Erwachsene | 1 | 24 € | [Amazon](https://www.amazon.de/dp/B082PXKWG6) |
| {haken('amazon_flansch')}Boxenflansch **Adam Hall SM 700** (Stahl 3 mm, Platte Ø 110 mm, Hülse 36 mm innen, 106 mm hoch) – Platte mit 4 Schrauben 4×16 **+ Unterlegscheiben M5** mittig unter die Kiste, Hülse nach unten; der zweite ist Reserve | 1 (2er-Set) | 19 € | [Amazon](https://www.amazon.de/dp/B09YDD368S) |

Kiste sitzt immer oben auf dem Stativ. Fenstermitte damit {P.STATIV_MIN + P.FLANSCH_PLATTE[2] + M.fenster_mitte_im_rahmen():.0f}–{P.STATIV_MAX + P.FLANSCH_PLATTE[2] + M.fenster_mitte_im_rahmen():.0f} mm: Kinder {P.KIND_FENSTERMITTE} mm, Erwachsene {P.ERW_FENSTERMITTE} mm.

## Noch offen
Software (Anzeige, Rangliste) – kommt erst, wenn die Hardware läuft
"""
(Path(__file__).parent / "Einkaufsliste.md").write_text(einkauf, encoding="utf-8")

# Blender-Stufen und Wokwi-Projekt gleich mit erneuern, damit nichts veraltet
# (danach in Blender blender_laden.py ausführen)
import stufen  # noqa: E402
import wokwi  # noqa: E402

stufen.export_stufen()
wokwi.export()
print(f"\nFertig -> {AUS}")
