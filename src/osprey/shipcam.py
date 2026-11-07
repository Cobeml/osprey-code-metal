"""Ship deck camera: rail-crossing MOB trigger (FR-01) and camera-frame geometry.

A person tracked on the deck camera arms the trigger when their depth Z < rail_m (on deck).
After arming it fires when Z > rail_m + hysteresis for >= n_frames consecutive frames, or when
the track is lost (missing >= lost_after_s) within lost_window_s of having been at Z > rail_m - 0.3.
Exactly one trigger per arming; reset() re-arms after End Incident.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


def box_depth_m(depth_mm: np.ndarray, bbox_px: tuple[int, int, int, int]) -> Optional[float]:
    """Median valid depth (m) in the inner 50% of the box (by width and height)."""
    x1, y1, x2, y2 = bbox_px
    w, h = x2 - x1, y2 - y1
    if w <= 1 or h <= 1:
        return None
    ix1, ix2 = int(x1 + 0.25 * w), int(x2 - 0.25 * w)
    iy1, iy2 = int(y1 + 0.25 * h), int(y2 - 0.25 * h)
    patch = depth_mm[max(iy1, 0):max(iy2, 1), max(ix1, 0):max(ix2, 1)]
    v = patch[patch > 0]
    if v.size < 10:
        return None
    return float(np.median(v)) / 1000.0


def lateral_m(cx_px: float, z_m: float, fx: float, cx0: float) -> float:
    """Camera-frame X (right, m) of a box center at depth z."""
    return (cx_px - cx0) * z_m / fx


@dataclass
class _TrackHist:
    last_ts: float
    last_z: Optional[float]
    last_x: float = 0.0
    near_ts: Optional[float] = None  # last time Z > rail - 0.3
    beyond: int = 0                   # consecutive frames Z > rail + hyst
    armed: bool = False


@dataclass
class RailTrigger:
    rail_m: float = 1.5
    hysteresis_m: float = 0.15
    n_frames: int = 3
    lost_window_s: float = 1.5
    lost_after_s: float = 0.4
    near_margin_m: float = 0.3
    fired: bool = False
    tracks: dict = field(default_factory=dict)

    def reset(self) -> None:
        self.fired = False
        self.tracks = {}

    @property
    def armed(self) -> bool:
        return not self.fired and any(t.armed for t in self.tracks.values())

    def update(self, ts: float, obs: list[tuple[int, Optional[float], float]]) -> Optional[dict]:
        """obs: (track_id, depth Z m or None, lateral X m) for every person this frame.
        Returns a trigger dict once per arming."""
        if self.fired:
            return None
        seen = set()
        for tid, z, x in obs:
            seen.add(tid)
            h = self.tracks.get(tid) or _TrackHist(ts, z, x)
            self.tracks[tid] = h
            h.last_ts = ts
            if z is None:
                continue
            h.last_z, h.last_x = z, x
            if z < self.rail_m:
                h.armed = True
            if z > self.rail_m - self.near_margin_m:
                h.near_ts = ts
            h.beyond = h.beyond + 1 if z > self.rail_m + self.hysteresis_m else 0
            if h.armed and h.beyond >= self.n_frames:
                return self._fire(ts, tid, h, "crossed rail")
        for tid, h in list(self.tracks.items()):
            if tid in seen:
                continue
            if ts - h.last_ts >= self.lost_after_s:
                if h.armed and h.near_ts is not None and h.last_ts - h.near_ts <= self.lost_window_s:
                    return self._fire(h.last_ts, tid, h, "lost from view at the rail")
                if ts - h.last_ts > 5.0:
                    del self.tracks[tid]
        return None

    def _fire(self, ts: float, tid: int, h: _TrackHist, why: str) -> dict:
        self.fired = True
        return {"ts": ts, "track_id": tid, "z_m": h.last_z, "x_m": h.last_x, "reason": why,
                "rail_m": self.rail_m}
