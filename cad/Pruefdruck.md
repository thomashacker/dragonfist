# Prüfdruck – zuerst drucken, dann erst alles andere

*Automatisch erzeugt von `build.py`. Dateien: `ausgabe/pruefdruck/`. Zusammen ca. 59 g PLA oder PETG,
gleiche Einstellungen wie später für die Endteile (0,2 mm Schicht, 3 Wände, 20 % Füllung, ohne Stützen).*

Jedes Stück ist ein Ausschnitt aus dem echten Teil – gleiche Maße, gleiche Passungen.
Passt ein Stück nicht: messen, Wert in `parameter.py` ändern (Zeilen mit `# MESSEN`), `python build.py`, neu drucken.

| Datei | Anzahl | Größe | Was prüfen |
|---|---|---|---|
| `1_Testblock_Sensoren.stl` | 2× | 160 × 25 × 33 mm | 3 Sensoren einlegen: sitzen sie stramm, liegt die LED mittig im Loch, passt die Schraube 2.5×16? Beide Blöcke im Abstand 297 mm gegenüberstellen: schaltet jeder Empfänger nur bei seinem eigenen Strahl (Übersprechen)? |
| `2_Huelsen_Ecke.stl` | 1× | 38 × 38 × 19 mm | Alu-Rohr 10×10 einstecken: leicht saugend, nicht wackelig. Passt eine Sensorader durch den Schlitz unten in der Hülse? |
| `3_Schwalbe_links.stl` | 1× | 33 × 16 × 4 mm | Mit 3_Schwalbe_rechts zusammenstecken: geht mit Daumendruck, ohne Spalt (wird später verklebt). |
| `3_Schwalbe_rechts.stl` | 1× | 25 × 16 × 4 mm | siehe 3_Schwalbe_links |
| `4_Knopf_Stueck.stl` | 1× | 44 × 106 × 31 mm | Arcade-Knopf einschrauben (Loch 28 mm). Unter der Platte messen: ist Knopf + Mikroschalter höchstens 33 mm tief? |
| `5_Kabelkanal_Stueck.stl` | 1× | 16 × 24 × 40 mm | USB-Kabel, 5-V-Kabel und 19-V-Kabel einlegen: passen alle drei, halten die Rastlippen sie fest? |
| `6_Nest_Teil1_Wagos.stl` | 1× | 116 × 59 × 10 mm | Endteil (später 2× gebraucht). Wago 221-415 einlegen: liegen sie ohne Klemmen in den Taschen, kommt man an die Einlässe und Hebel? |
| `6_Nest_Teil2_Board.stl` | 1× | 181 × 59 × 10 mm | Endteil (später 2× gebraucht). Breakout-Board mit Pico und Wagos einlegen: passt alles, lassen sich beide Nest-Teile am Schwalbenschwanz zusammenstecken (später verkleben)? |

## Reihenfolge
1. Sensoren (Adafruit) messen: Gehäuse, LED-Kuppe, Befestigungsloch → `parameter.py` → neu bauen → **dann** drucken.
2. Prüfteile drucken, mit den echten Teilen testen, Maße anpassen.
3. Display, Jetson-Lochabstand, Boxenflansch nachmessen (stehen ebenfalls mit `# MESSEN` in `parameter.py`).
4. Erst dann die Endteile aus `ausgabe/druck/` drucken (ca. 805 g).
