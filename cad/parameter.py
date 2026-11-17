"""
Alle Maße des Schlag-Messgeräts an einer Stelle (Millimeter).

Hier ändern, dann `build.py` neu laufen lassen – alle Teile, STEP/STL-Dateien,
die Zuschnittliste und die Vorschaubilder werden neu erzeugt.

Koordinaten:  X = Breite (links/rechts aus Sicht des Kindes)
              Y = Schlagrichtung (Kind steht bei negativem Y, schlägt Richtung +Y)
              Z = Höhe
Nullpunkt des Rahmens: Mitte der Vorderkante, Unterseite des unteren Bretts.

Werte mit  # MESSEN  sind Platzhalter, bis die echten Teile da sind.
"""

# ---------------------------------------------------------------------------
# Messfenster und Messebenen
# ---------------------------------------------------------------------------
# Alle vier Bretter haben dasselbe Maß (runde Zahlen, einfacher Zuschnitt):
#   oben/unten liegen zwischen den Seitenbrettern -> lichte Breite = Brettlänge,
#   Seitenbretter stehen -> Außenhöhe = Brettlänge. Fensterhöhe und Lage von A
#   werden am Dateiende daraus berechnet.
BRETT = (400, 250)            # Länge, Tiefe (Schlagrichtung) – alle 4 Bretter
FENSTER_BREITE = BRETT[0]     # lichte Breite zwischen den Seitenbrettern

# A liegt bewusst weit vor B: ein neuer Schlag zählt erst, wenn A wieder frei ist, also
# die Faust (samt Unterarm) wieder vor A ist. So muss zur Deckung zurückgezogen werden,
# Fuchteln knapp vor dem Fenster zählt nicht. Gemessen wird der Schnitt über A->B.
EBENENABSTAND_AB = 200        # 1 mm Fehler = 0,5 % Geschwindigkeitsfehler
# Hinten schließt das Gitter bündig mit der Brettkante ab (Anschlag beim Montieren).

# Strahlpositionen in X (0 = Mitte). Abstand 55 mm < Faustbreite (ca. 60 mm),
# damit jede Faust mindestens einen Strahl trifft. Gemessen wird nur in der Mitte,
# außerhalb zeigt die Software „daneben“.
STRAHLEN_A = [-150, -95, -40, 40, 95, 150]                 # 3 pro Seite
STRAHLEN_B = [-165, -110, -55, 0, 55, 110, 165]            # 7 Strahlen

TRENNUNG_A_BREITE = 20        # weicher Schaumstoffstreifen in Ebene A, Mitte
TRENNUNG_A_TIEFE = 30

# ---------------------------------------------------------------------------
# Sensor: Adafruit IR Break Beam 5 mm (2168), Sender und Empfänger gleiches Gehäuse.
# Das Gehäuse LIEGT flach, die LED schaut oben heraus, das Kabel kommt an einer
# Stirnseite raus, daneben ein durchgehendes Befestigungsloch.
# ---------------------------------------------------------------------------
SENSOR_LAENGE = 20.0          # gemessen 20 (07.11.); Länge = Kabelrichtung
SENSOR_BREITE = 10.0          # gemessen ≈ 10
SENSOR_HOEHE = 8.0            # gemessen 8, ohne LED-Kuppe
LED_DURCHMESSER = 5.0         # MESSEN  (5-mm-LED)
LED_UEBERSTAND = 5.0          # gemessen: Höhe mit LED 13 – Gehäuse 8
LED_VON_STIRN = 5.0           # gemessen: LED-Mitte 15 mm vom Kabelende = 5 mm von der Stirnseite
LOCH_VON_KABEL = 5.0          # gemessen: Befestigungsloch-Mitte 5 mm vom Kabelende
SENSOR_SCHRAUBE_D = 2.7       # Durchgang im Halter für Holzschraube 2,5 x 16 (Loch im Sensor gemessen ≈ 3 mm)

# Kabel zeigen in den Raum zwischen A und B: A-Sensoren nach hinten, B-Sensoren nach vorne.
# So bleibt das Gitter hinten bündig und alle Kabel laufen in der Mitte zusammen.
KABEL_RICHTUNG = {"A": +1, "B": -1}

SPIEL = 0.3                   # Passungsspiel für Taschen und Bohrungen (Drucker abhängig)

# Blendtunnel gegen Übersprechen (vor der LED, im Türmchen).
# Öffnungswinkel ca. atan(D/L) muss kleiner sein als der Winkel zum Nachbarstrahl
# (55 mm auf 340 mm = 9,2°) – build.py prüft das und meldet es.
TUNNEL_DURCHMESSER = 2.5
TUNNEL_LAENGE = 20.0

# ---------------------------------------------------------------------------
# Gedruckte Sensorplatte (dünnes Gitter + ein Türmchen pro Sensor)
# ---------------------------------------------------------------------------
PLATTE_DICKE = 4              # Gitter liegt flach auf dem Brett
STREIFEN_BREITE = 16          # Streifen unter jeder Ebene (in Y); bestimmt mit A–B die Drucktiefe
RIPPE_BREITE = 10             # Querrippen, halten A und B auf exaktem Abstand
SCHRAUBAUGE_D = 14            # Verbreiterung der Rippe um die Schraube
TURM_WAND = 2.0               # Wandstärke um die Sensortasche und Dach über dem Sensor
MIT_LIPPE = False             # Anschlag über die Brettvorderkante; ohne: mit Zollstock ausrichten
LIPPE_TIEFE = 12              #   (oben/unten dürfen ca. 2 cm versetzt sein, bevor der Tunnel abschattet)
LIPPE_DICKE = 4

LEISTE_TEILUNGEN = [10]       # Trennfugen der Plattenstücke (nicht durch ein Türmchen!)
SCHWALBE = (8, 6, 10)         # Schwalbenschwanz an der Fuge: Länge, Breite an der Fuge, Breite am Ende
SCHWALBE_SPIEL = 0.15         # je Seite; Teile werden zusätzlich verklebt

# Sensorkäfig: obere und untere Platte über 4 Pfosten fest verbunden
PFOSTEN = 10                  # Alu-Vierkantrohr 10 x 10 mm (Baumarkt), mit Metallsäge kürzen
PFOSTEN_LUFT = 1              # so viel kürzer als das Maß zwischen den Platten: zu lang klemmt, zu kurz stört nicht
HUELSE_HOEHE = 15             # Steckhülse auf der Platte
HUELSE_WAND = 3
LEISTE_LUFT_SEITLICH = 0.5    # Luft zwischen Platte und Seitenbrett, je Seite

KABELKERBE = (7, 6)           # Ausschnitt hinten im Turmfuß für das Kabel (Breite, Höhe)

SCHRAUBE_D = 4.5              # Durchgang für Halbrundschraube 4 x 16

DRUCKBETT = (256, 256)        # eigener Drucker: Bambu Lab A1 (256 x 256 x 256 mm)
GPIO_FREI = 26                # Raspberry Pi Pico: GP0–GP22 + GP26–GP28

# ---------------------------------------------------------------------------
# Holzrahmen
# ---------------------------------------------------------------------------
BRETT_DICKE = 18              # Leimholz Kiefer 18 mm (Baumarkt-Zuschnitt)
SCHWIMMNUDEL_D = 60
# Bretter stumpf verleimt + verschraubt (keine Winkel innen – dort sitzt der Sensorkäfig)
RAHMEN_SCHRAUBEN_JE_ECKE = 3

# ---------------------------------------------------------------------------
# Schrauben (Durchmesser, Länge)
# ---------------------------------------------------------------------------
SCHRAUBE_SENSOR = (2.5, 16)   # durch Halterdach + Befestigungsloch ins Brett
SCHRAUBE_GITTER = (4, 16)     # Halbrundschraube, Gitter ans Brett
SCHRAUBE_RAHMEN = (4, 50)     # Seitenbrett in Stirnholz von Brett oben/unten

# ---------------------------------------------------------------------------
# Kabelführung und Elektronik
#   Pico + Wagos liegen in einem gedruckten Nest MITTEN zwischen A und B (unter dem
#   Fenster). Sensorkabel laufen in Kanälen neben den Haltern dorthin – sie reichen
#   ohne Verlängerung. Die Sender oben bekommen 5 V/GND über 2 Adern im hohlen
#   hinteren linken Alu-Pfosten. Raus gehen nur USB (Jetson) und 5 V (Netzteil).
# ---------------------------------------------------------------------------
KANAL_INNEN = (12, 12)        # Kabelkanal innen: Breite (Y), Höhe
KANAL_WAND = 1.6
KANAL_CLIP = 1.2              # Rastlippe oben innen, hält die Adern im Kanal
KANAL_ABSTAND = 1.5           # Luft zwischen Sensorhalter und Kanal
EINFUEHRUNG = 8               # Schlitz in der Kanalwand vor jedem Halter

NEST_WAND = 1.6
NEST_BODEN = 2
NEST_HOEHE = 8                # Wände des Nests (Teile werden nur gehalten, nicht eingeklemmt)
NEST_SCHRAUBEN = 2            # Halbrundschrauben 4x16 je Nest (Teile sind verklebt)

HUELSE_SCHLITZ = (6, 6)       # Kabelaustritt unten in der Pfostenhülse (Breite, Höhe)
KABEL_PFOSTEN = "hinten links"  # dieser Pfosten führt die 2 Adern für die Sender oben

PICO_BOARD = (73, 55, 21)     # gemessen mit Pico drauf (07.11.): Länge X, Breite Y, Höhe
PICO = (51, 21, 4)            # Raspberry Pi Pico 2 H
WAGO = (30, 18, 8)            # gemessen (07.11.) Wago 221-415: Breite mit den 5 Einlässen (nebeneinander in x), Tiefe in Einsteckrichtung (y), Höhe
DC_KUPPLUNG = (38, 14)        # gemessen goobay 76743: Länge (Buchse bis Klemme), Dicke
SENSORKABEL = 250             # Kabellänge am Sensor (Datenblatt)
# LEDs: WS2812B-Streifen auf der Vorderseite der vorderen Alu-Pfosten (10 mm breit wie das Rohr),
# also links und rechts am Fensterrand im Blick des Kindes
GPIO_LED = {"links": 16, "rechts": 19}   # je ein Datenpin, keine Kette übers Fenster
LED_PRO_M = 60                # WS2812B 60 LEDs/m, 5 V
LED_STROM_MA = 60             # pro LED bei voller weißer Helligkeit
LED_HELLIGKEIT = 0.35         # Firmware begrenzt darauf (schont Netzteil und Augen)
LED_STREIFEN = (10, 2.5)      # Breite, Dicke des Streifens (klebt auf dem Pfosten)

# Deckel über dem Mittelfeld (Nest, Wagos, Adern), auf Säulen, 2 Hälften
DECKEL_DICKE = 2
DECKEL_LUFT = 3               # Abstand über dem höchsten Teil darunter (Pico-Board 21 mm hoch)
DECKEL_SAEULE_D = 9
DECKEL_SCHUERZE = 1.6         # Wand vorne/hinten vom Deckel bis auf die Kabelkanäle (blickdicht)
DECKEL_FUGE = 0               # Schürze liegt auf der Kanaloberkante auf (stützt den Deckel über die ganze Länge)
NETZTEIL_A = 4.0              # MeanWell 5 V / 4 A

# Kabelkanal außen hinten am linken Seitenbrett (gedruckt, 2 Teile): USB Pico -> Jetson,
# 5 V Netzteil -> Kiste, 19 V Netzteil -> Jetson laufen darin senkrecht
KABELKANAL_INNEN = (20, 14)   # Breite (Y), Tiefe (X) innen – 3 Kabel à ca. 4–5 mm
KABELKANAL_WAND = 2
KABELKANAL_RAND_HINTEN = 6    # Abstand zur hinteren Brettkante

# ---------------------------------------------------------------------------
# Bedienpult oben auf der Kiste (gedruckt): 7"-Display im Wire-Mod-Rahmen, Jetson darin,
# Arcade-Knöpfe über USB-Encoder am Jetson; USB-Lautsprecher außen daneben auf der Kiste
# ---------------------------------------------------------------------------
PULT_BREITE = 210             # passt auf ein 220er-Druckbett
PULT_TIEFE = 200
PULT_WAND = 3
# Seitenprofil (y nach hinten, z nach oben): vorne Knopfleiste ~15°, dahinter Display ~70° steil
PULT_PROFIL = [(0, 0), (0, 40), (60, 56), (100, 166), (200, 166), (200, 0)]
DISPLAY = (165, 100, 20)      # MESSEN  7" HDMI-Display (z. B. Waveshare 7inch HDMI LCD (C)): B, H, Tiefe
DISPLAY_FENSTER = (156, 88)   # MESSEN  sichtbare Fläche
JETSON = (103, 91, 35)        # MESSEN  Jetson Orin Nano Developer Kit mit Kühler: L, B, H
JETSON_LOECHER = (86, 58)     # MESSEN  Lochabstand der Befestigungslöcher (M2.5)
LAUTSPRECHER = (100, 25, 45)  # MESSEN  HuaLiSiJi Mini-USB-Soundbar: B, T, H – steht AUSSEN rechts neben dem Pult
KNOPF_LOCH = 28               # Arcade-Knopf 30 mm braucht 28-mm-Bohrung
KNOEPFE = ["Zurück", "◀", "START", "▶", "OK"]   # von links nach rechts; START in der Mitte
KNOPF_ABSTAND = 40
KNOPF_TIEFE = 33              # Einbautiefe unter der Platte (Knopf + Mikroschalter)

# ---------------------------------------------------------------------------
# Stativ und Aufhängung
# ---------------------------------------------------------------------------
STATIV_ROHR_D = 35
STATIV_UNTERROHR_D = 38
STATIV_MIN = 670              # Pronomic SPS-5S (niedrig): 67–120 cm, 35 mm, 50 kg
STATIV_MAX = 1200
STATIV_BEIN_RADIUS = 550      # Fußkreis-Radius
STATIV_SPINNE_Z = 550         # Höhe, an der die Beine am Rohr ansetzen

FLANSCH_PLATTE = (110, 110, 3) # Adam Hall SM 700: Platte Ø 110 mm, 3 mm Stahl, Löcher 9 mm
FLANSCH_TOPF = (42, 103)      # Hülse (innen 36 mm), Gesamthöhe 106 mm – Außen-Ø MESSEN

# Kinder und Erwachsene: Kiste sitzt mit Boxenflansch oben auf dem Stativ (kein Hängewinkel)
KIND_FENSTERMITTE = 900       # Höhe Fenstermitte über Boden

ERW_FENSTERMITTE = 1350

# ---------------------------------------------------------------------------
# Sonstiges
# ---------------------------------------------------------------------------
STANDMARKE_Y = -450           # Klebeband-Markierung Fußspitze (nur Darstellung)

# ---------------------------------------------------------------------------
# Aus dem Brettmaß abgeleitet (nicht von Hand ändern)
# ---------------------------------------------------------------------------
RAHMEN_TIEFE = BRETT[1]
RAND_VORNE = RAHMEN_TIEFE - STREIFEN_BREITE / 2 - EBENENABSTAND_AB      # Brettvorderkante -> Ebene A
EBENE_A_VON_VORNE = RAND_VORNE
_HALTER = SENSOR_HOEHE + SPIEL + LED_UEBERSTAND + TUNNEL_LAENGE
FENSTER_HOEHE = BRETT[0] - 2 * BRETT_DICKE - 2 * _HALTER                 # freie Höhe zwischen den Haltern
