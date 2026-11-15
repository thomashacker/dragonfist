# Prüfbericht Hardware – Stand 01.11.2026

Geprüft am Modell (`build.py` + `pruefen.py`) und gegen Datenblätter. Wiederholen nach jeder Änderung:
`python build.py` (Maß-, Strom-, Kabel-, Pin-Prüfungen) und `python pruefen.py` (Kollisionen).

## Mechanik
| Prüfung | Ergebnis |
|---|---|
| Kollisionen aller festen Teile (Bretter, Platten, Halter, Sensoren, Pfosten, Nest, Wagos, Pico, Deckel, LEDs, Pult, Kabelkanal, Schrauben) | ✅ keine – 4 Fehler im Pult gefunden und behoben (Lautsprecher/Eckblock, USB-Encoder/Jetson, 2 Knöpfe/Eckblöcke) |
| Druckteile passen auf 220×220-Bett | ✅ alle; Pult-Gehäuse braucht 180 mm Bauhöhe + Stützen |
| Deckel unterhalb der Strahlen | ✅ Oberkante 32 mm, Strahlen ab 33 mm (Pico-Board gemessen 21 mm hoch, 3 mm Luft darüber; Brücken laufen neben dem Board) |
| Sensor-Kabel reichen ohne Verlängerung | ✅ längster Weg 205 mm, Kabel 250 mm |

## Strom
| Verbraucher | Strom (max.) |
|---|---|
| 13 Sender (20 mA) + 13 Empfänger | ca. 0,3 A |
| 38 LEDs (60 mA bei voll weiß) | 2,3 A – Firmware begrenzt auf 35 % → ca. 0,8 A |
| **Summe am 5-V-Netzteil (4 A)** | **max. 2,6 A → ✅ Reserve** |
| Pico, Display (~0,5 A), Lautsprecher, Knopf-Encoder | über USB vom Jetson ✅ |
| Jetson | eigenes 19-V-Netzteil ✅ |

Leitungen: LED-Strom (bis 1,2 A je Seite) und Brücke links↔rechts in **20 AWG (0,5 mm²)** ✅,
Zuleitung Sender oben 0,3 A ✅, Sensoradern nur mA ✅.

## Masse und Pegel
| Prüfung | Ergebnis |
|---|---|
| Gemeinsame Masse Netzteil – Sensoren – LEDs – Pico | ✅ Pico-GND (Pin 3) an Wago GND; Jetson über USB |
| Pico-VBUS/VSYS **nicht** an 5 V | ✅ in Anleitung festgehalten |
| Empfänger-Ausgang (Open Collector) an 3,3-V-Pico | ✅ nur interner Pull-up, nie 5 V an einen GPIO |
| LED-Daten 3,3 V an 5-V-WS2812B | ⚠️ knapp außerhalb der Norm, geht meist – Pegelwandler bereithalten |
| **Neu ergänzt:** 330 Ω in jede LED-Datenleitung, 1000 µF am Netzteil-Eingang | ✅ in Verkabelung + Einkaufsliste |

## Pins (gegen offizielles Pico-Pinout geprüft)
13 Sensoren auf GP0, 3, 6, 9, 12, 15 (Ebene A) und GP28, 27, 26, 21, 20, 18, 17 (Ebene B),
LEDs auf GP16 / GP19, GND Pin 3 – alles echte GPIOs, nichts doppelt, keine Sonderpins. ✅

## Noch offen – erst mit echten Teilen prüfbar
- Sensormaße, LED-Position, Befestigungsloch (→ `# MESSEN` in `parameter.py`), dann **Testblock drucken**
- Übersprechen/Tunnel mit 3 Sensoren auf dem Schreibtisch
- ~~Breakout-Board RPIP-BRB-1: führt es alle Pins auf Schraubklemmen?~~ ✅ geprüft am echten Board: 2 × 20 Klemmen, alle 40 Pico-Pins
- ~~Sensormaße~~ ✅ gemessen (20 × 10 × 8 mm, LED 5 mm über, Loch 5 mm vom Kabelende) und eingetragen
- Maße Display, Jetson-Lochbild, Lautsprecher (Pult)
- Polung DC-Kupplung mit Multimeter, bevor zum ersten Mal Strom drauf ist
