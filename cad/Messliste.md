# Messliste – echte Teile nachmessen

Mit dem Messschieber auf 0,1 mm messen und eintragen (oder Foto mit angelegtem Messschieber schicken).
Die Werte kommen in `parameter.py` (Zeilen mit `# MESSEN`), danach `python build.py`.

## 1. Sensoren Adafruit 2168 – wichtigste Messung (vor dem Prüfdruck)
An **einem Sender und einem Empfänger** messen:

| Maß | Im Modell | Gemessen Sender | Gemessen Empfänger |
|---|---|---|---|
| Gehäuse Länge (Kabelrichtung) | 20,0 mm | 20 ✅ | |
| Gehäuse Breite | 10,0 mm | ≈ 10 ✅ | |
| Gehäuse Höhe (ohne LED) | 8,0 mm | 8 ✅ | |
| LED-Durchmesser | 5,0 mm | | |
| LED steht oben über das Gehäuse hinaus | 5,0 mm | 5 (13 − 8) ✅ | |
| LED-Mitte bis Gehäuseende **ohne** Kabel | 5,0 mm | 5 (15 vom Kabelende) ✅ | |
| Befestigungsloch: Durchmesser | ca. 2,7 mm | ≈ 3 ✅ | |
| Befestigungsloch-Mitte bis Gehäuseende **mit** Kabel | 6,0 → 5,0 mm | 5 ✅ | |
| Kabellänge (bis zum Aderende) | 250 mm | etwas über 250 ✅ | |

Dazu: Steht die LED genau in der Mitte der Breite? Ja / Nein (wie weit daneben?)

## 2. Elektronik-Nest (vor dem Prüfdruck)

| Teil | Maß | Im Modell | Gemessen |
|---|---|---|---|
| Breakout-Board RPIP-BRB-1 | Länge × Breite × Höhe (mit Pico drauf) | 73 × 54 × 12 mm | 73 × 55 × 21 ✅ |
| Wago 221-415 | Breite × Länge × Höhe | 19 × 37 × 16 mm | 30 × 18 × 8 ✅ |
| Elko 1000 µF | Durchmesser × Länge | 10 × 17 mm | 10 × 17 ✅ (laut Packung) |
| DC-Kupplung goobay 76743 | Länge × Breite × Höhe | 38 × 14 mm | 38 × 14 ✅ |

Dazu: Führt das Breakout-Board **alle** Pins GP0–GP28 und GND auf Schraubklemmen heraus? **Ja ✅ (2 × 20 Klemmen)**

## 3. Bedienpult (vor dem Pult-Druck)

| Teil | Maß | Im Modell | Gemessen |
|---|---|---|---|
| Display ELECROW 7" | Platine B × H × Tiefe (mit Anschlüssen) | 165 × 100 × 20 mm | |
| Display | sichtbare Bildfläche B × H | 156 × 88 mm | |
| Display | Abstand der 4 Befestigungslöcher B × H, Lochdurchmesser | – | |
| Display | Wo sitzen HDMI- und USB-Buchse? (Foto reicht) | – | |
| Jetson Orin Nano | L × B × H mit Kühler | 103 × 91 × 35 mm | |
| Jetson Orin Nano | Abstand der 4 Befestigungslöcher | 86 × 58 mm | |
| Arcade-Knopf | Einbautiefe unter der Platte (Rand bis Ende Mikroschalter) | max. 33 mm | |
| Arcade-Knopf | Gewindedurchmesser | 28 mm Loch | |
| USB-Encoder | Platine L × B × H (mit Steckern) | 70 × 30 × 8 mm | |
| USB-Lautsprecher | B × T × H, Abstand der Ösen | 100 × 25 × 45 mm | |

## 4. Aufbau (wenn er da ist)

| Teil | Maß | Im Modell | Gemessen |
|---|---|---|---|
| Boxenflansch Adam Hall SM 700 | Hülse außen Ø | 42 mm | |
| Boxenflansch | Lochkreis bzw. Abstand der Befestigungslöcher | – | |
| Stativ Pronomic SPS-5S | kleinste / größte Höhe Oberkante Rohr | 670 / 1200 mm | |
| Holzbretter (alle 4) | Länge × Breite × Dicke | 400 × 250 × 18 mm | |
| Alu-Pfosten (alle 4, nach dem Sägen) | Länge | 356 mm | |
