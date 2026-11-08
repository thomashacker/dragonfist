WRAP = 1 << 30
SETTLE_S = 0.03
MAX_DT_US = 2_000_000
MIN_DT_US = 8_000


class Punch:
    def __init__(self, n_a, n_ch, dist_mm):
        self.amask = (1 << n_a) - 1
        self.all = (1 << n_ch) - 1
        self.n_a, self.dist = n_a, dist_mm / 1000
        self.low, self.ph, self.clear = 0, None, None
        self.ta = self.tb = self.ach = self.bch = None
        self.n = 0
        self.last = None
        self.best = 0.0

    def edge(self, i, v, tus, now):
        if v:
            self.low &= ~(1 << i)
        else:
            self.low |= 1 << i
            if i < self.n_a:
                if self.ph is None:
                    self.ph, self.ta, self.ach, self.bch = "A", tus, i, None
            elif self.ph == "A":
                self.ph, self.tb, self.bch = "AB", tus, i
            elif self.ph is None:
                self.ph, self.ach, self.bch = "B", None, i
        self.clear = now if not self.low else None

    def status(self, mask, now):
        self.low = ~mask & self.all
        if self.low:
            self.clear = None
        elif self.clear is None:
            self.clear = now

    def tick(self, now):
        if self.ph is None or self.low or self.clear is None or now - self.clear < SETTLE_S:
            return None
        ph, self.ph = self.ph, None
        a = self.ach if self.ach is not None else self.bch
        side = None if a is None else (a if a < self.n_a else a - self.n_a) / self.n_a
        hand = None if side is None else ("L" if side < 0.5 else "R")
        r = dict(t=now, ok=False, v=None, dt=None, a=self.ach, b=self.bch, hand=hand)
        if ph == "AB":
            dt = (self.tb - self.ta) % WRAP
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
        else:
            r["msg"] = "NICHT DURCH" if ph == "A" else "RÜCKWÄRTS"
        self.last = r
        return r
