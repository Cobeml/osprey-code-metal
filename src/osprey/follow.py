"""Scout A follow commands (FR-11/FR-13).

Follow errors are sent while the incident is active, following is enabled and the rover holds
the confirmed target. "stop" is sent only when following is disabled (Stop following, or no
active incident); while the rover searches on its own camera lock after launch, nothing is sent. The message carries the normalized error of the target box center from the frame center;
the rover runs its own rate-limited P loop on the pan-tilt servos and holds when commands go stale
(> 1 s, e.g. visual loss or link loss). Stop always wins.
"""
from __future__ import annotations

from typing import Optional


class FollowController:
    def __init__(self, idle_period_s: float = 0.5):
        self.idle_period_s = idle_period_s
        self._last_idle = 0.0
        self._last_kind: Optional[str] = None

    def on_frame(self, following: bool, follow_enabled: bool, target_bbox: Optional[tuple],
                 capture_ts: float, now: float) -> Optional[dict]:
        if following and target_bbox is not None:
            x1, y1, x2, y2 = target_bbox
            ex, ey = (x1 + x2) / 2 - 0.5, (y1 + y2) / 2 - 0.5
            self._last_kind = "follow"
            return {"type": "follow", "err": [round(ex, 4), round(ey, 4)],
                    "size": round(y2 - y1, 4), "capture_ts": capture_ts}
        if not follow_enabled:
            kind = "stop"          # coordinator stopped following, or no active incident
        elif following:
            kind = "hold"          # confirmed target, box momentarily missing
        else:
            return None            # rover searching on its own lock after launch: don't stop it
        if kind != self._last_kind or now - self._last_idle >= self.idle_period_s:
            self._last_kind = kind
            self._last_idle = now
            return {"type": kind}
        return None
