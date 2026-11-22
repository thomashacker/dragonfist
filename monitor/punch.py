WRAP = 1 << 30
SETTLE_S = 0.03
MAX_DT_US = 2_000_000
MIN_DT_US = 8_000
DEAD_S = 5.0


def _bits(r):
    return sum(1 << i for i in r)


class Seite:
    """Eine Hand: A brechen -> B brechen -> wieder ganz frei = Schlag."""

    def __init__(self, hand, a, b, shared):
        self.hand, self.a, self.b, self.shared = hand, a, b, shared
        self.ph = self.ta = self.tb = self.ach = self.bch = self.clear = self.tbr = self.tar = None
        self.m = 0

    def mask(self):
        m = self.a | self.b
        return m if self.ph else m & ~self.shared


class Punch:
    def __init__(self, n_a, n_ch, dist_mm):
        nb, ha = n_ch - n_a, n_a // 2
        hb = (nb + 1) // 2
        self.amask, self.all, self.n_a, self.dist = (1 << n_a) - 1, (1 << n_ch) - 1, n_a, dist_mm / 1000
        links = _bits(range(n_a, n_a + hb))
        rechts = _bits(range(n_ch - hb, n_ch))
        shared = links & rechts
        self.seiten = (Seite("L", _bits(range(ha)), links, shared), Seite("R", _bits(range(ha, n_a)), rechts, shared))
        self.low, self.dead, self.n, self.last, self.best = 0, 0, 0, None, 0.0
        self.events = []

    @property
    def ph(self):
        return next((s.ph for s in self.seiten if s.ph), None)

    def reset(self):
        self.low = 0
        for s in self.seiten:
            s.ph = None

    def _clear(self, now):
        for s in self.seiten:
            if self.low & s.mask():
                s.clear = None
            elif s.clear is None:
                s.clear = now

    def edge(self, i, v, tus, now):
        bit = 1 << i
        if v:
            self.low &= ~bit
            for s in self.seiten:
                if s.ph == "AB":
                    if bit & s.b and not self.low & s.b:
                        s.tbr = tus
                    elif bit & s.a and not self.low & s.a:
                        s.tar = tus
        else:
            self.low |= bit
            for s in self.seiten:
                if bit & s.a:
                    if s.ph is None:
                        s.ph, s.ta, s.ach, s.bch, s.tbr, s.tar, s.m = "A", tus, i, None, None, None, 0
                        self.events.append(("a", s.hand))
                elif bit & s.b:
                    if s.ph == "A":
                        s.ph, s.tb, s.bch = "AB", tus, i
                        self.events.append(("b", s.hand))
                    elif s.ph is None and not bit & s.shared:
                        s.ph, s.ach, s.bch, s.m = "B", None, i, 0
                if s.ph and bit & (s.a | s.b):
                    s.m |= bit
        self._clear(now)

    def set_dead(self, mask, now):
        if mask == self.dead:
            return
        neu = mask & ~self.dead
        for s in self.seiten:
            if neu & (s.a | s.b):
                s.ph = None
        self.dead = mask
        self.low &= ~mask
        self._clear(now)

    def status(self, mask, now):
        self.low = ~mask & self.all & ~self.dead
        self._clear(now)

    def tick(self, now):
        out = []
        for s in self.seiten:
            if s.ph is None or s.clear is None or now - s.clear < SETTLE_S:
                continue
            ph, s.ph = s.ph, None
            r = dict(t=now, ok=False, v=None, vb=None, dt=None, a=s.ach, b=s.bch, hand=s.hand, am=s.m & s.a,
                     bm=s.m & s.b)
            if ph == "AB":
                dt = (s.tb - s.ta) % WRAP
                r["dt"] = dt
                if dt < MIN_DT_US:
                    r["msg"] = "ZU SCHNELL?"
                elif dt > MAX_DT_US:
                    r["msg"] = "ZU LANGSAM"
                else:
                    self.n += 1
                    v = self.dist * 1e6 / dt
                    self.best = max(self.best, v)
                    r.update(ok=True, v=v, n=self.n, msg="TREFFER")
                    if s.tbr is not None and s.tar is not None:
                        db = (s.tar - s.tbr) % WRAP
                        if MIN_DT_US <= db <= MAX_DT_US:
                            r["vb"] = self.dist * 1e6 / db
            else:
                r["msg"] = "NICHT DURCH" if ph == "A" else "RÜCKWÄRTS"
            self.events.append(("punkt" if r["ok"] else "fehl", s.hand))
            self.last = r
            out.append(r)
        return out
