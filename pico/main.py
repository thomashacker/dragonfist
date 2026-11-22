import sys, time, machine, rp2, select
from machine import Pin, ADC, mem32
from ubinascii import hexlify

VERSION = 3
A = (0, 3, 6, 9, 12, 15)
B = (28, 27, 22, 21, 14, 18, 17)
CH = A + B
SIO_IN = 0xD0000004

for g in CH:
    Pin(g, Pin.IN, Pin.PULL_UP)
vbus = Pin(24, Pin.IN)
vsys = ADC(Pin(29))
temp = ADC(4)
uid = hexlify(machine.unique_id()).decode()
w = sys.stdout.write

N_LED, HELL = 19, 0.35
RUHE, BRUCH = (40, 0, 0), (255, 140, 40)


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24,
             fifo_join=rp2.PIO.JOIN_TX)
def ws2812():
    wrap_target()
    label("bit")
    out(x, 1).side(0)[2]
    jmp(not_x, "null").side(1)[1]
    jmp("bit").side(1)[4]
    label("null")
    nop().side(0)[4]
    wrap()


def wort(c):
    r, g, b = (int(v * HELL) for v in c)
    return (g << 16 | r << 8 | b) << 8


class Streifen:
    """Füttert den PIO-FIFO stückweise aus der Hauptschleife – blockiert die Abtastung nie."""

    def __init__(self, nr, pin):
        self.sm = rp2.StateMachine(nr, ws2812, freq=8_000_000, sideset_base=Pin(pin))
        self.sm.active(1)
        self.buf, self.i, self.farbe = [0] * N_LED, N_LED, None

    def setze(self, c, n=N_LED):
        if (c, n) != self.farbe:
            self.farbe = (c, n)
            v = wort(c)
            self.bild([v if k < n else 0 for k in range(N_LED)])

    def bild(self, buf):
        self.buf, self.i = buf, 0
        if self not in AKTIV:
            AKTIV.append(self)

    def pumpe(self):
        while self.i < N_LED and self.sm.tx_fifo() < 8:
            self.sm.put(self.buf[self.i])
            self.i += 1


AKTIV = []
LED = (Streifen(0, 16), Streifen(1, 19))
for k in range(N_LED + 1):
    for s in LED:
        s.setze(RUHE, k)
        while s.i < N_LED:
            s.pumpe()
    time.sleep_ms(25)
SEITE = (0x3C7, 0x1E38)    # Kanalmasken links (A1–A3, B1–B4) / rechts (A4–A6, B4–B7)


def _rad(h):
    h, k = h % 96, h % 32 * 8
    return (255 - k, k, 0) if h < 32 else (0, 255 - k, k) if h < 64 else (k, 0, 255 - k)


RAD = [wort(_rad(h)) for h in range(96)]
pl = select.poll()
pl.register(sys.stdin, select.POLLIN)
modus, zeile, t_cmd, f = "auto", "", 0, 0    # auto: Pico färbt selbst · host: App setzt Farben · tanz: Regenbogen


def befehl(p):
    global modus
    if len(p) == 3 and p[0] == "L":
        modus = "host"
        for s, x in zip(LED, p[1:]):
            v = int(x, 16)
            s.setze((v >> 16, v >> 8 & 255, v & 255))
    elif p == ["T"]:
        modus = "tanz"
    else:
        return False
    return True


def auto(raw):
    m = chmask(raw)
    for s, k in zip(LED, SEITE):
        s.setze(RUHE if m & k == k else BRUCH)

PM = 0
for g in CH:
    PM |= 1 << g


def chmask(raw):
    m = 0
    for i, g in enumerate(CH):
        if raw >> g & 1:
            m |= 1 << i
    return m


def temp_dc():
    v = temp.read_u16() * 3.3 / 65535
    return int((27 - (v - 0.706) / 0.001721) * 10)


wdt = machine.WDT(timeout=8000)    # hängt das Programm, startet der Pico neu (mpremote cp + reset passt darunter)
last = mem32[SIO_IN] & PM
t_s = t_h = t_i = time.ticks_ms()
n = 0
while True:
    raw = mem32[SIO_IN] & PM
    d = raw ^ last
    if d:
        t = time.ticks_us()
        for i, g in enumerate(CH):
            if d >> g & 1:
                w("E %d %d %d\n" % (i, raw >> g & 1, t))
        last = raw
        if modus == "auto":
            auto(raw)
    if AKTIV:
        for s in AKTIV:
            s.pumpe()
        AKTIV[:] = [s for s in AKTIV if s.i < N_LED]
    n += 1
    now = time.ticks_ms()
    if time.ticks_diff(now, t_s) >= 50:
        t_s = now
        wdt.feed()
        w("S %x\n" % chmask(raw))
        while pl.poll(0):
            c = sys.stdin.read(1)
            if c == "\n":
                try:
                    if befehl(zeile.split()):
                        t_cmd = now
                except ValueError:
                    pass
                zeile = ""
            elif len(zeile) < 40:
                zeile += c
        if modus == "tanz":
            f += 1
            for k, s in enumerate(LED):
                s.farbe = None
                s.bild([RAD[(i * 5 + f * 2 + k * 48) % 96] for i in range(N_LED)])
        if modus != "auto" and time.ticks_diff(now, t_cmd) > 3000:
            modus = "auto"
            for s in LED:
                s.farbe = None
            auto(raw)
        dt = time.ticks_diff(now, t_h)
        if dt >= 500:
            t_h = now
            w("H %d %d %d %d %d\n" % (vbus.value(), vsys.read_u16() * 9900 // 65535, temp_dc(), n * 1000 // dt, now))
            n = 0
        if time.ticks_diff(now, t_i) >= 2000:
            t_i = now
            w("I %d %s %d %d\n" % (VERSION, uid, len(A), len(B)))
