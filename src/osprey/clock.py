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
    """Accelerated clock used ONLY for drift integration. Freshness and outage timing always use
    the real clock. Changing the multiplier keeps simulated elapsed time continuous."""

    def __init__(self, clock: Clock, multiplier: float = 60.0):
        self.clock = clock
        self.multiplier = multiplier
        self._anchor_real = clock.now()
        self._anchor_sim = 0.0

    def sim_elapsed(self) -> float:
        return self._anchor_sim + (self.clock.now() - self._anchor_real) * self.multiplier

    def set_multiplier(self, m: float) -> None:
        self._anchor_sim = self.sim_elapsed()
        self._anchor_real = self.clock.now()
        self.multiplier = float(m)

    def reset(self) -> None:
        self._anchor_real = self.clock.now()
        self._anchor_sim = 0.0
