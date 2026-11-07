"""Scenario: ship pose and the simulated person truth used for scout coordinates.

Scouts have no real geolocation (PRD). Their reported person location is this hidden truth plus
noise, labeled "simulated". The truth drifts with a *different* leeway class (PIW-2) and its own
random draws on the scenario clock (fast only while no sighting is fresh); the estimator (drift.py, PIW-1, accelerated clock) never reads it.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .contracts import Location
from .drift import Forcing, LeewayEnsemble
from .geo import LatLon, ShipPose, enu_to_latlon, latlon_to_enu, offset_by_bearing

SCOUT_NOISE_M = 3.0
SCOUT_ACCURACY_M = 8.0
ACQUIRE_DELAY_S = {"A": 4.0, "B": 9.0}  # sim scouts "reach" the area after MOB


class Scenario:
    def __init__(self, ship: ShipPose, forcing: Forcing, sim_at=None, seed: int = 7):
        self.sim_at = sim_at or (lambda t: t)  # real ts -> scenario seconds
        self.ship = ship
        self.forcing = forcing
        self.rng = np.random.default_rng(seed)
        self.truth: Optional[LeewayEnsemble] = None
        self.t_mob: Optional[float] = None
        self.hidden = False  # sim scouts cannot see the person (demo "hide")

    def on_mob(self, location: Optional[Location], ts: float) -> None:
        p = LatLon(location.lat, location.lon) if location else self.ship.origin
        self.truth = LeewayEnsemble(p, self.forcing, n=1, obj="PIW-2",
                                    rng=np.random.default_rng(self.rng.integers(1 << 31)),
                                    seed_sigma_m=0.0, diffusivity=0.05)
        self.t_mob = ts
        self.hidden = False

    def end(self) -> None:
        self.truth = None
        self.t_mob = None
        self.hidden = False

    def truth_latlon(self, now: float) -> Optional[LatLon]:
        if self.truth is None:
            return None
        self.truth.advance_to(max(0.0, self.sim_at(now) - self.sim_at(self.t_mob)), dt=5.0)
        x, y = self.truth.xy[0]
        return enu_to_latlon(self.truth.origin, float(x), float(y))

    def place(self, ref: LatLon, bearing_deg: float, dist_m: float, now: float) -> None:
        """Demo: the person reappears dist_m from `ref` along bearing (e.g. toward the estimate)."""
        if self.truth is None:
            return
        self.truth_latlon(now)
        target = offset_by_bearing(ref, bearing_deg, dist_m)
        x, y = latlon_to_enu(self.truth.origin, target)
        self.truth.xy[0] = np.array([x, y])

    def launched(self, node_id: str, now: float) -> bool:
        return self.t_mob is not None and now - self.t_mob >= ACQUIRE_DELAY_S.get(node_id, 0.0)

    def scout_location(self, node_id: str, now: float) -> Optional[Location]:
        p = self.truth_latlon(now)
        if p is None:
            return None
        nx, ny = self.rng.normal(0.0, SCOUT_NOISE_M, 2)
        q = enu_to_latlon(p, float(nx), float(ny))
        return Location(lat=q.lat, lon=q.lon, provenance="simulated", quality="good",
                        accuracy_m=SCOUT_ACCURACY_M)
