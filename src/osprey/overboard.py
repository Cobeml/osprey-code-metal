"""Ball-overboard trigger: the deck camera loses the green ball AND the water sensor is wet.

The trigger arms once the deck camera has seen the green ball (it is "on deck"). It fires once
per arming when the ball has been out of view for >= lost_after_s while the water sensor reads
wet. The order doesn't matter: ball lost then water, or water then ball lost. reset() re-arms
after End Incident.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BallWaterTrigger:
    lost_after_s: float = 0.5
    fired: bool = False
    armed_since: Optional[float] = None
    last_seen: Optional[float] = None
    last_fix: Optional[dict] = None  # {"x_m", "z_m"} where the ball was last seen

    def reset(self) -> None:
        self.fired = False
        self.armed_since = self.last_seen = self.last_fix = None

    @property
    def armed(self) -> bool:
        return not self.fired and self.armed_since is not None

    def ball_seen(self, now: float, x_m: Optional[float] = None, z_m: Optional[float] = None) -> None:
        if self.fired:
            return
        if self.armed_since is None:
            self.armed_since = now
        self.last_seen = now
        if z_m is not None:
            self.last_fix = {"x_m": x_m or 0.0, "z_m": z_m}

    def in_view(self, now: float) -> bool:
        return self.last_seen is not None and now - self.last_seen < self.lost_after_s

    def update(self, now: float, wet: bool) -> Optional[dict]:
        """Returns a trigger dict once per arming."""
        if not self.armed or not wet or self.in_view(now):
            return None
        self.fired = True
        f = self.last_fix or {}
        return {"ts": now, "reason": "green ball lost from the deck camera + water sensor wet",
                "last_seen_ts": self.last_seen, "x_m": f.get("x_m"), "z_m": f.get("z_m")}
