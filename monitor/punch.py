WRAP = 1 << 30
SETTLE_S = 0.025
MAX_DT_US = 2_000_000
MIN_DT_US = 8_000
DEAD_S = 5.0
LERN = 0.2                      # wie schnell die typische Position jeder Hand nachgeführt wird
BREITE = 2                      # so viele nebeneinanderliegende A-Strahlen deckt eine Faust höchstens ab
ZUCKEN_S = 0.08                 # nur A, kürzer als das: kein Fehlschlag, sondern Arm im Vorbeiwischen
NACH_US = 40_000                # B so lange frei, dann zählt ein neuer B-Stoß bei Arm in A als neuer Schlag
NACH_MIN_DT_US = 20_000         # kürzer (> 36 km/h) ist beim Nachschlag kein Messwert: Schlag zählt ohne Tempo
RUTSCH_US = 6_000               # Nachbarstrahl in A so kurz vorher frei geworden: Arm rutscht seitlich, kein Schlagbeginn
V_MAX = 40 / 3.6                # schneller ist keine Faust auf 20 cm: Schlag zählt ohne Tempo


class Faust:
    """Ein zusammenhängender Körper im Fenster: A brechen -> B brechen -> beide Ebenen wieder frei = Schlag."""
    __slots__ = ("hand", "ph", "a", "b", "m", "ta", "tb", "tbr", "tar", "ach", "bch", "clear", "t0", "tan", "arm")

    def __init__(self, hand, ph, i, tus, now):
        self.hand, self.ph, self.a, self.b, self.m, self.t0, self.arm = hand, ph, 0, 0, 0, now, False
        self.ta = self.tan = tus if ph == "A" else None
        self.tb = self.tbr = self.tar = self.clear = None
        self.ach, self.bch = (i, None) if ph == "A" else (None, i)

    def vorwaerts(self):
        return self.ph == "A" or bool(self.b)


class Punch:
    def __init__(self, n_a, n_ch, dist_mm):
        self.n_a, self.n_b = n_a, n_ch - n_a
        self.amask, self.all, self.dist = (1 << n_a) - 1, (1 << n_ch) - 1, dist_mm / 1000
        self.faeuste, self.hx = [], {"L": 0.35, "R": 0.65}
        self.low, self.dead, self.n, self.last, self.best = 0, 0, 0, None, 0.0
        self.frei = [None] * n_a
        self.events, self.fertig = [], []

    @property
    def ph(self):
        return next((f.ph for f in self.faeuste), None)

    def reset(self):
        self.low, self.faeuste, self.fertig = 0, [], []

    def pos(self, i):
        return (i + 0.5) / self.n_a if i < self.n_a else (i - self.n_a + 0.5) / self.n_b

    def x(self, f):
        bits = [i for i in range(self.n_a) if f.m >> i & 1] or [i for i in range(self.n_a, self.n_a + self.n_b)
                                                                    if f.m >> i & 1]
        return sum(map(self.pos, bits)) / len(bits)

    def _neu(self, ph, i, tus, now):
        x, andere = self.pos(i), self.faeuste
        if len(andere) == 1:
            xo = self.x(andere[0])
            hand = ("L" if x < xo else "R") if abs(x - xo) > 0.1 else "R" if andere[0].hand == "L" else "L"
        else:
            hand = min("LR", key=lambda h: abs(self.hx[h] - x))
        f = Faust(hand, ph, i, tus, now)
        if ph == "A" and any(0 <= j < self.n_a and self.frei[j] is not None
                             and (tus - self.frei[j]) % WRAP < RUTSCH_US for j in (i - 1, i + 1)):
            f.ta = None
        f.arm = any(g.b for g in andere)
        self.faeuste.append(f)
        ph == "A" and self.events.append(("a", hand))
        return f

    def _besitzer_a(self, i):
        bit = 1 << i
        for f in self.faeuste:
            if f.m & bit or f.ph == "B":
                return f
        for f in self.faeuste:
            idx = [k for k in range(self.n_a) if f.a >> k & 1]
            if f.vorwaerts() and idx and min(idx) - 1 <= i <= max(idx) + 1 \
                    and max(idx + [i]) - min(idx + [i]) < BREITE:
                return f

    def edge(self, i, v, tus, now):
        bit = 1 << i
        if bit & self.dead:
            return
        if v:
            self.low &= ~bit
            if i < self.n_a:
                self.frei[i] = tus
            for f in self.faeuste:
                if (f.a | f.b) & bit:
                    f.a &= ~bit
                    f.b &= ~bit
                    if f.ph == "AB":
                        if i >= self.n_a and not f.b:
                            f.tbr = tus
                        elif i < self.n_a and not f.a:
                            f.tar = tus
                    if not f.a | f.b:
                        f.clear = now
            return
        self.low |= bit
        if i < self.n_a:
            f = self._besitzer_a(i) or self._neu("A", i, tus, now)
            f.a |= bit
            f.tan = tus
        else:
            x, nach = self.pos(i), (bit << 1 | bit >> 1) & ~self.amask & self.all
            f = next((f for f in self.faeuste if f.b & nach), None)
            if f is None:
                kand = sorted(self.faeuste, key=lambda f: abs(self.x(f) - x) + (0 if f.vorwaerts() else 0.3))
                f = kand[0] if kand else self._neu("B", i, tus, now)
            if f.ph == "AB" and not f.b and f.tbr is not None and (tus - f.tbr) % WRAP >= NACH_US:
                f = self._nachschlag(f, i, tus, now)
            if f.ph == "A":
                f.ph, f.tb, f.bch = "AB", tus, i
                self.events.append(("b", f.hand))
            f.b |= bit
            for g in self.faeuste:
                g.arm |= g.ph == "A"
            f.arm = False
        f.m |= bit
        f.clear = None

    def _frei(self, now):
        for f in self.faeuste:
            f.a &= self.low
            f.b &= self.low
            if not f.a | f.b and f.clear is None:
                f.clear = now

    def set_dead(self, mask, now):
        if mask != self.dead:
            self.dead = mask
            self.low &= ~mask
            self._frei(now)

    def status(self, mask, now):
        self.low = ~mask & self.all & ~self.dead
        self._frei(now)

    def _nachschlag(self, f, i, tus, now):
        """Faust war schon aus B zurück, Arm blieb in A, und sie stößt erneut durch B: alter Schlag fertig, neuer beginnt."""
        self.faeuste.remove(f)
        self.fertig.append(self._ergebnis(f, now))
        g = Faust(f.hand, "A", f.ach, tus, now)
        frisch = f.tan is not None and (f.tan - f.tbr) % WRAP < (tus - f.tbr) % WRAP \
            and (tus - f.tan) % WRAP >= NACH_MIN_DT_US
        g.ta = g.tan = f.tan if frisch else None
        g.a = g.m = f.a
        self.faeuste.append(g)
        return g

    def _ergebnis(self, f, now):
        r = dict(t=now, ok=False, v=None, vb=None, dt=None, a=f.ach, b=f.bch, hand=f.hand, am=f.m & self.amask,
                 bm=f.m & ~self.amask)
        if f.ph == "AB":
            dt = None if f.ta is None else (f.tb - f.ta) % WRAP
            r["dt"] = dt
            if dt is not None and dt < MIN_DT_US:
                r["msg"] = "ZU SCHNELL?"
            elif dt is not None and dt > MAX_DT_US:
                r["msg"] = "ZU LANGSAM"
            else:
                self.n += 1
                r.update(ok=True, n=self.n, msg="TREFFER")
                h = self.hx[f.hand] + LERN * (self.x(f) - self.hx[f.hand])
                self.hx[f.hand] = min(h, 0.45) if f.hand == "L" else max(h, 0.55)
                if dt and self.dist * 1e6 / dt <= V_MAX:
                    r["v"] = self.dist * 1e6 / dt
                    self.best = max(self.best, r["v"])
                if f.tbr is not None and f.tar is not None:
                    db = (f.tar - f.tbr) % WRAP
                    if MIN_DT_US <= db <= MAX_DT_US and self.dist * 1e6 / db <= V_MAX:
                        r["vb"] = self.dist * 1e6 / db
        else:
            r["msg"] = "NICHT DURCH" if f.ph == "A" else "RÜCKWÄRTS"
        self.events.append(("punkt" if r["ok"] else "fehl", f.hand))
        self.last = r
        return r

    def tick(self, now):
        out, self.fertig = self.fertig, []
        for f in [f for f in self.faeuste if f.clear is not None and now - f.clear >= SETTLE_S]:
            self.faeuste.remove(f)
            if not (f.ph == "A" and (f.arm or f.clear - f.t0 < ZUCKEN_S)):
                out.append(self._ergebnis(f, now))
        return out
