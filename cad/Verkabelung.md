# Verkabelung – Schlag-Messgerät

*Automatisch erzeugt von `build.py` – nicht von Hand ändern.* Plan als Bild: `ausgabe/Verkabelung.svg`

## Wo was sitzt
- **Elektronik-Nest unten** (Druckteil, mittig zwischen A und B): Pico 2 H auf Schraubklemmen-Board,
  links und rechts davon je eine Reihe Wago 5V und GND (unten: 5V 4× links + 2× rechts, GND 4× links + 2× rechts).
  Sensoren links gehen in die linken Wagos, rechts in die rechten; beide Seiten sind gebrückt.
  Liegt unter dem Messfenster, keine Faust kommt hin.
- **Nest oben** (gleiches Druckteil): nur Wagos für die Sender (5V 2× links + 2× rechts, GND 2× links + 2× rechts).
- **Kabelkanäle** direkt neben den Sensorhaltern, mit Einführschlitz je Halter und Rastlippe.
  Sensorkabel (25 cm) reichen ohne Verlängerung (längster Weg ca. 21 cm).
- **Zuleitung zu den Sendern**: 2 Adern 0,5 mm² durch den hohlen hinteren linken Alu-Pfosten.
- **Raus** gehen nur USB (Pico → Jetson) und das 5-V-Netzteil, hinten links über die Kante.
- **Deckel** (gedruckt, 2 Hälften je Platte) liegt auf 4 Säulen über dem Mittelfeld und versteckt Nest, Wagos
  und Adern; 4 Schrauben 2.5×16 je Deckel – zum Basteln einfach abschrauben.

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
- Je ein WS2812B-Streifen (19 LEDs je Seite, 60/m) links und rechts am Fensterrand.
- Sitzen auf der **Vorderseite der vorderen Alu-Pfosten** (Streifen 10 mm = Rohr 10 mm), Klebeband hinten
  vom Streifen abziehen und aufkleben, **Pfeile nach oben** (Daten kommen von unten).
- 1-m-Streifen kaufen und teilen: das Stück **mit** Stecker nach links, das zweite Stück bekommt einen
  **lötfreien Klemmverbinder** (3-polig, 10 mm) mit Kabel.
- Je Seite 3 Adern: rot → Wago 5V, schwarz → Wago GND, Daten → Pico (Tabelle unten).
  Weg: Kanal A zur Seite, durch den Schlitz vor dem Pfosten, innen an der Hülse vorbei zum unteren Streifenende.
- Strom: max. 2.3 A bei voller Helligkeit; die Firmware begrenzt auf 35%
  → ca. 0.8 A. Netzteil 4 A reicht.
- **330-Ω-Widerstand in jede Datenleitung** (Pflicht): ein Bein in die Pico-Klemme (GP-Pin), das andere mit der
  gelben LED-Datenader in eine Wago 221-412. Schützt den Pico, wenn die LEDs noch keinen Strom haben.
- **Kondensator 1000 µF / 10 V** an den Netzteil-Eingang: langes Bein (+) in Wago 5V links, kurzes Bein (−, Streifen
  auf dem Gehäuse) in Wago GND links. **Polung beachten** – falsch herum kann er platzen.
- Flackern die LEDs trotzdem: Pegelwandler (3,3 V → 5 V, z. B. 74AHCT125) in die Datenleitung.

## Pinbelegung (Empfänger-Signal)
| Nr | Ebene | Seite | Position | Pico | Pin |
|---|---|---|---|---|---|
| 1 | A | links | -150 mm | GP0 | 1 |
| 2 | A | links | -95 mm | GP3 | 5 |
| 3 | A | links | -40 mm | GP6 | 9 |
| 4 | A | rechts | +40 mm | GP9 | 12 |
| 5 | A | rechts | +95 mm | GP12 | 16 |
| 6 | A | rechts | +150 mm | GP15 | 20 |
| 7 | B | links | -165 mm | GP28 | 34 |
| 8 | B | links | -110 mm | GP27 | 32 |
| 9 | B | links | -55 mm | GP26 | 31 |
| 10 | B | Mitte | +0 mm | GP21 | 27 |
| 11 | B | rechts | +55 mm | GP20 | 26 |
| 12 | B | rechts | +110 mm | GP18 | 24 |
| 13 | B | rechts | +165 mm | GP17 | 22 |
| – | – | – | – | GND | 3 → Wago GND unten |
| – | LED | links | – | GP16 | 21 → Daten LED-Streifen links |
| – | LED | rechts | – | GP19 | 25 → Daten LED-Streifen rechts |

## Reihenfolge
1. Sensoren in die Halter legen, je eine Schraube 2.5×16 durchs Loch.
2. Adern durch den Einführschlitz in den Kanal drücken, bis die Rastlippe sie hält; zum Nest führen.
3. Jede gelbe Ader mit ihrer Nummer beschriften (Klebeband), dann in die Klemme laut Tabelle.
4. Rot/schwarz in die Wago-Reihen; die Wagos einer Reihe mit einem kurzen Drahtstück verbinden.
5. 2 Adern (rot, schwarz) unten durch den Hülsen-Schlitz in den hinteren linken Pfosten, oben wieder raus,
   oben in Wago 5V/GND. (Am Rohr unten und oben je eine 6-mm-Kerbe aussägen.)
6. Pico-GND an Wago GND unten. **Pico-VBUS / VSYS bleiben frei** – der Pico bekommt Strom nur über USB. DC-Kupplung (Schraubklemmen + / −) liegt links neben dem Nest (Buchse nach hinten zum Kabelaustritt), mit 2 kurzen Drähten an Wago 5V/GND links
   links unten; Polung vor dem ersten Einstecken mit dem Multimeter prüfen. USB-Kabel an den Pico.
7. Erst testen (Strahlen unterbrechen, Anzeige im Terminal), dann den Käfig in die Kiste schieben.
