"""Clocks: real server clock, injectable fake clock, per-source offset estimation, scenario clock.

All server-side times are float seconds in the server's wall-clock domain (time.time()).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


class Clock:
    def now(self) -> float:
        return time.time()


class FakeClock(Clock):
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


@dataclass
class OffsetEstimator:
    """Estimates a sender's clock offset (server - sender) from ping round trips.

    The sender sends {"ping": t_send_sender}; the server echoes it with its own time t_srv;
    the sender replies {"pong": t_send_sender, "srv": t_srv, "recv": t_recv_sender}.
    offset = t_srv - (t_send + t_recv) / 2 (NTP-style). We keep the sample with the smallest RTT
    from the recent window, which is the least affected by queueing.
    """

    window: int = 20
    samples: deque = field(default_factory=lambda: deque(maxlen=20))

    def add(self, t_send: float, t_srv: float, t_recv: float) -> None:
        rtt = t_recv - t_send
        if rtt < 0:
            return
        self.samples.append((rtt, t_srv - (t_send + t_recv) / 2.0))

    @property
    def quality(self) -> str:
        if len(self.samples) >= 3 and min(s[0] for s in self.samples) < 0.25:
            return "synced"
        if self.samples:
            return "estimated"
        return "unknown"

    @property
    def offset(self) -> float | None:
        if not self.samples:
            return None
        return min(self.samples)[1]

    @property
    def rtt(self) -> float | None:
        return min(self.samples)[0] if self.samples else None

    def to_server(self, sender_ts: float, received_ts: float) -> float:
        """Convert a sender capture time to the server domain. Without samples, fall back to the
        receive time (honest upper bound on freshness). Never return a time in the future."""
        off = self.offset
        if off is None:
            return received_ts
        return min(sender_ts + off, received_ts)


class ScenarioClock:
    """Accelerated scenario clock, used ONLY for drift integration and the simulated person truth.
    Freshness and outage timing always use the real clock.

    The clock runs at `multiplier` while `fast` (no sighting is fresh) and at 1x otherwise, so the
    displayed estimate and the simulated world share one timeline. Changing the rate keeps
    simulated time continuous; sim_at() answers for past real times too.
    """

    def __init__(self, clock: Clock, multiplier: float = 60.0, fast: bool = True):
        self.clock = clock
        self.multiplier = float(multiplier)
        self.fast = fast
        self._segs: list[tuple[float, float, float]] = [(clock.now(), 0.0, self.rate)]

    @property
    def rate(self) -> float:
        return self.multiplier if self.fast else 1.0

    def sim_at(self, real_ts: float) -> float:
        seg = self._segs[0]
        for s in self._segs:
            if s[0] <= real_ts:
                seg = s
            else:
                break
        return seg[1] + (real_ts - seg[0]) * seg[2]

    def sim_elapsed(self) -> float:
        return self.sim_at(self.clock.now())

    def set_multiplier(self, m: float) -> None:
        sim_now = self.sim_elapsed()
        self.multiplier = float(m)
        self._segs.append((self.clock.now(), sim_now, self.rate))

    def set_fast(self, fast: bool) -> None:
        if fast != self.fast:
            sim_now = self.sim_elapsed()
            self.fast = fast
            self._segs.append((self.clock.now(), sim_now, self.rate))
