import sys, time, machine
from machine import Pin, ADC, mem32
from ubinascii import hexlify

VERSION = 1
A = (0, 3, 6, 9, 12, 15)
B = (28, 27, 26, 21, 20, 18, 17)
CH = A + B
SIO_IN = 0xD0000004

for g in CH:
    Pin(g, Pin.IN, Pin.PULL_UP)
vbus = Pin(24, Pin.IN)
vsys = ADC(Pin(29))
temp = ADC(4)
uid = hexlify(machine.unique_id()).decode()
w = sys.stdout.write

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
    n += 1
    now = time.ticks_ms()
    if time.ticks_diff(now, t_s) >= 50:
        t_s = now
        w("S %x\n" % chmask(raw))
        dt = time.ticks_diff(now, t_h)
        if dt >= 500:
            t_h = now
            w("H %d %d %d %d %d\n" % (vbus.value(), vsys.read_u16() * 9900 // 65535, temp_dc(), n * 1000 // dt, now))
            n = 0
        if time.ticks_diff(now, t_i) >= 2000:
            t_i = now
            w("I %d %s %d %d\n" % (VERSION, uid, len(A), len(B)))
