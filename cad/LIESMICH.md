# Schlag-Messgerät VVD – CAD (build123d)

## Nach jeder Änderung

1. Maße in `parameter.py` ändern.
2. `%USERPROFILE%\b123d\Scripts\python build.py` – erneuert Druckteile, STEP, Bericht,
   **Einkaufsliste.md** und die Blender-Stufen.
3. In Blender `Schlagmesser.blend` → `blender_laden.py` ausführen – ersetzt alle Collections.
4. Optional Bilder: `%USERPROFILE%\b123d\Scripts\python vorschau.py`

Die Python-Umgebung liegt unter `%USERPROFILE%\b123d`, weil OpenCascade mit langen
Windows-Pfaden nicht zurechtkommt.

## Blender-Collections

| Collection | Inhalt |
|---|---|
| `1_Rahmen` … `7_Bedienpult` | zusammen die fertige Kiste (Holz, Sensoren, Käfig, Schrauben, Elektronik, LEDs + Deckel, Pult mit Display, Jetson, Knöpfen) |
| `6_Gitter_ohne_Pfosten` | oberes + unteres Gitter in Einbaulage, daneben |
| `7_Kaefig_mit_Sensoren_und_Kabeln` | Käfig mit Pfosten, Sensoren, Schrauben, Wago, Kabeln |
| `8_Druckteile_flach` | Druckteile wie auf dem Druckbett, Testblock davor |
| `9_Elektronik_Nest` | unteres Nest frei daneben: Pico, Wago-Reihen links/rechts, Adern-Enden |

Weitere erzeugte Dateien: `Einkaufsliste.md`, `Verkabelung.md` (Anleitung, Pinbelegung),
`ausgabe/Verkabelung.svg` (maßstäbliche Draufsicht mit allen Adern, gleiche Wege wie in 3D),
`ausgabe/pins.json` (dieselbe Pinbelegung für die Pico-Firmware),
`wokwi/` (Simulation im Browser: Schaltplan + Messlogik in MicroPython, Anleitung in `wokwi/LIESMICH.md`).

Elektronik: Pico und Wagos liegen im gedruckten Nest mittig zwischen A und B, die Adern laufen
in Kabelkanälen mit Rastlippe dorthin (ohne Verlängerung). Die Sender oben bekommen 5 V/GND über
2 Adern im hinteren linken Alu-Pfosten. Raus gehen nur USB (Jetson) und 5 V (Netzteil).

## Aufbau

- Holzkiste innen 40 cm breit, 25,3 cm tief, Fenster 30 cm hoch.
- Ebenen A und B, **200 mm** Abstand: ein Schlag zählt erst wieder, wenn die Faust vor A
  zurückgezogen ist (kein Fuchteln).
- 13 Lichtschranken (A: 6, B: 7, Raster 55 mm).
- **Sensorkäfig**: gedrucktes Gitter oben + unten (je 2 Hälften mit Schwalbenschwanz,
  verklebt), verbunden durch 4 Alu-Vierkantrohre 10×10. Fertig bestücken, testen,
  von hinten in die Kiste schieben (hinten bündig, seitlich anliegend), festschrauben.

## Annahmen, die noch zu prüfen sind

- Sensor liegt flach (20 × 10 × 8 mm laut Datenblatt). Aus dem Foto geschätzt, **messen**:
  LED-Kuppe 5 mm hoch, LED-Mitte 5 mm von der Stirnseite, Befestigungsloch 6 mm von der
  Kabelseite (`LED_*`, `LOCH_VON_KABEL`, `SENSOR_SCHRAUBE_D` in parameter.py).
- Stativ 1100–1800 mm → Datenblatt des echten Stativs eintragen.
- Blendtunnel 2,5 × 20 mm → mit dem Prototyp-Testblock prüfen.
- Firmware: Zeitfenster A→B bei 200 mm auf ca. 300 ms setzen (Plan sagt 150 ms).
