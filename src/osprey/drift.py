"""Monte Carlo leeway drift for a person in the water (FR-06).

Velocity of each particle = surface current + leeway(10 m wind) + random-walk diffusion.

Leeway coefficients are the published person-in-water (PIW) values from
  Allen, A. A. and Plourde, J. V. (1999), "Review of Leeway: Field Experiments and Implementation",
  US Coast Guard R&D Center report CG-D-08-99,
as tabulated in the SAROPS object list maintained by O. Breivik (met.no, 2011) and distributed
with OpenDrift (opendrift/models/OBJECTPROP.DAT). Columns: downwind slope [% of U10],
downwind offset [cm/s], downwind std [cm/s], right/left crosswind slope [%], offset [cm/s], std.
The perturbation scheme (eps ~ N(0, std) per particle, applied as eps/20 to the slope and eps/2 to
the offset, jibing between left and right crosswind) follows OpenDrift's leeway.py.

The estimator uses PIW-1 (unknown state, mean values). The scenario truth (scenario.py) uses a
different class (PIW-2) and its own noise, and never feeds the estimator.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from .geo import LatLon, enu_to_latlon, latlon_to_enu

# name: (dw_slope, dw_offset, dw_std, cwr_slope, cwr_offset, cwr_std, cwl_slope, cwl_offset, cwl_std)
LEEWAY = {
    "PIW-1": ("Person-in-water, unknown state (mean values)",
              (0.96, 0.00, 12.00, 0.54, 0.00, 9.40, -0.54, 0.00, 9.40)),
    "PIW-2": ("PIW, vertical PFD type III conscious",
              (0.48, 0.00, 8.30, 0.15, 0.00, 6.70, -0.15, 0.00, 6.70)),
    "PIW-6": ("PIW, deceased (face down)",
              (1.117, 10.2, 3.04, 0.04, 3.90, 4.05, -0.04, -3.90, 4.05)),
}
JIBE_PROB_PER_HOUR = 0.04   # OpenDrift leeway default
DIFFUSIVITY_M2_S = 0.5      # horizontal random-walk diffusivity (assumption, labeled in UI)

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Forcing:
    """Hourly wind (m/s, direction FROM, deg) and surface current (m/s, direction TOWARD, deg)."""

    t0_iso: str
    wind_speed: list
    wind_from_deg: list
    current_speed: list
    current_toward_deg: list
    label: str
    source: str
    is_default: bool = False

    def at(self, hours: float) -> tuple[float, float, float, float]:
        """(wind_u, wind_v, cur_u, cur_v) in m/s, ENU, at `hours` after t0 (linear interp)."""
        n = len(self.wind_speed)
        h = min(max(hours, 0.0), n - 1.0)
        i = int(math.floor(h))
        j = min(i + 1, n - 1)
        f = h - i

        def vec(spd, deg, toward):
            u = [s * math.sin(math.radians(d)) for s, d in ((spd[i], deg[i]), (spd[j], deg[j]))]
            v = [s * math.cos(math.radians(d)) for s, d in ((spd[i], deg[i]), (spd[j], deg[j]))]
            sign = 1 if toward else -1
            return sign * (u[0] * (1 - f) + u[1] * f), sign * (v[0] * (1 - f) + v[1] * f)

        wu, wv = vec(self.wind_speed, self.wind_from_deg, toward=False)
        cu, cv = vec(self.current_speed, self.current_toward_deg, toward=True)
        return wu, wv, cu, cv

    @classmethod
    def default(cls) -> "Forcing":
        return cls("—", [8.0] * 2, [225.0] * 2, [0.25] * 2, [100.0] * 2,
                   label="DEFAULT forcing (no environmental snapshot loaded)",
                   source="built-in constant: wind 8 m/s from SW, current 0.25 m/s toward E",
                   is_default=True)

    @classmethod
    def load(cls, path: str = "") -> "Forcing":
        p = Path(path) if path else None
        if p is None:
            cands = sorted((ROOT / "fixtures/env").glob("massbay-*.json"))
            p = cands[-1] if cands else None
        if p is None or not p.exists():
            return cls.default()
        d = json.loads(p.read_text())
        prov = d["provenance"]
        return cls(
            t0_iso=d["hourly"]["time"][0],
            wind_speed=d["hourly"]["wind_speed_10m"],
            wind_from_deg=d["hourly"]["wind_direction_10m"],
            current_speed=d["hourly"]["ocean_current_velocity"],
            current_toward_deg=d["hourly"]["ocean_current_direction"],
            label=f"Open-Meteo {prov['fetched_utc'][:10]}, Mass Bay {prov['lat']:.2f}N {abs(prov['lon']):.2f}W",
            source=f"{prov['forecast_url']} + {prov['marine_url']}",
        )


def convex_hull(pts: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain. pts: (n, 2). Returns hull vertices counter-clockwise."""
    p = np.unique(pts, axis=0)
    if len(p) < 3:
        return p
    p = p[np.lexsort((p[:, 1], p[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(tuple(q))
    for q in p[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(tuple(q))
    return np.array(lower[:-1] + upper[:-1])


def polygon_area(h: np.ndarray) -> float:
    if len(h) < 3:
        return 0.0
    x, y = h[:, 0], h[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


class LeewayEnsemble:
    """Particles in local ENU meters around a seed point."""

    def __init__(self, seed: LatLon, forcing: Forcing, n: int = 1500, obj: str = "PIW-1",
                 rng: Optional[np.random.Generator] = None, seed_sigma_m: float = 3.0,
                 forcing_offset_h: float = 0.0, diffusivity: float = DIFFUSIVITY_M2_S):
        self.origin = seed
        self.forcing = forcing
        self.obj = obj
        self.rng = rng or np.random.default_rng()
        self.diffusivity = diffusivity
        self.forcing_offset_h = forcing_offset_h
        c = LEEWAY[obj][1]
        self.c = c
        self.xy = self.rng.normal(0.0, seed_sigma_m, size=(n, 2))
        self.eps_dw = self.rng.normal(0.0, c[2], n)
        # redraw negative downwind slopes, as OpenDrift does
        bad = c[0] + self.eps_dw / 20.0 < 0
        while bad.any():
            self.eps_dw[bad] = self.rng.normal(0.0, c[2], bad.sum())
            bad = c[0] + self.eps_dw / 20.0 < 0
        self.right = np.arange(n) % 2 == 0
        self.eps_cw = np.where(self.right, self.rng.normal(0.0, c[5], n), self.rng.normal(0.0, c[8], n))
        self.t = 0.0  # simulated seconds since seed

    def _velocity(self) -> np.ndarray:
        wu, wv, cu, cv = self.forcing.at(self.forcing_offset_h + self.t / 3600.0)
        w = math.hypot(wu, wv)
        c = self.c
        dw_slope, cw_slope = c[0] + self.eps_dw / 20.0, np.where(self.right, c[3], c[6]) + self.eps_cw / 20.0
        dw_off = c[1] + self.eps_dw / 2.0
        cw_off = np.where(self.right, c[4], c[7]) + self.eps_cw / 2.0
        dwl = (dw_slope * w + dw_off) * 0.01  # m/s
        cwl = (cw_slope * w + cw_off) * 0.01
        if w > 1e-6:
            ex, ey = wu / w, wv / w  # unit vector downwind
        else:
            ex, ey = 0.0, 0.0
        # right of downwind = rotate (ex, ey) by -90 deg -> (ey, -ex)
        vx = cu + dwl * ex + cwl * ey
        vy = cv + dwl * ey - cwl * ex
        return np.stack([vx, vy], axis=1)

    def advance_to(self, t_sim: float, dt: float = 60.0) -> None:
        while self.t < t_sim - 1e-9:
            h = min(dt, t_sim - self.t)
            self.xy += self._velocity() * h
            self.xy += self.rng.normal(0.0, math.sqrt(2 * self.diffusivity * h), self.xy.shape)
            flip = self.rng.random(len(self.right)) < JIBE_PROB_PER_HOUR * h / 3600.0
            if flip.any():
                self.right[flip] = ~self.right[flip]
            self.t += h

    def hull(self, frac: float) -> np.ndarray:
        """Convex hull of the `frac` particles closest to the ensemble median (ENU m)."""
        center = np.median(self.xy, axis=0)
        d = np.linalg.norm(self.xy - center, axis=1)
        k = max(3, int(len(d) * frac))
        inner = self.xy[np.argsort(d)[:k]]
        return convex_hull(inner)

    def hull_latlon(self, frac: float) -> list[list[float]]:
        out = []
        for x, y in self.hull(frac):
            p = enu_to_latlon(self.origin, float(x), float(y))
            out.append([p.lat, p.lon])
        return out

    def centroid_latlon(self) -> list[float]:
        c = np.median(self.xy, axis=0)
        p = enu_to_latlon(self.origin, float(c[0]), float(c[1]))
        return [p.lat, p.lon]


class DriftEstimator:
    """Owns the displayed estimate: seeds from the engine's drift seed, suspended while fresh."""

    def __init__(self, forcing: Forcing, n: int = 1500):
        self.forcing = forcing
        self.n = n
        self.ens: Optional[LeewayEnsemble] = None
        self.seed_key: Optional[tuple] = None
        self.seed_info: Optional[dict] = None
        self.sim_at_seed: float = 0.0

    def clear(self) -> None:
        self.ens = None
        self.seed_key = None
        self.seed_info = None

    def update(self, seed: Optional[dict], fresh: bool, sim_at, multiplier: float,
               real_now: float) -> Optional[dict]:
        """seed: engine.drift_seed(); fresh: any sighting fresh; sim_at(real_ts) -> scenario s."""
        if seed is None or fresh:
            self.clear()
            return None
        loc = seed["location"]
        key = (seed["kind"], seed["ts"], round(loc.lat, 7), round(loc.lon, 7))
        if key != self.seed_key:
            self.seed_key = key
            self.seed_info = seed
            self.ens = LeewayEnsemble(LatLon(loc.lat, loc.lon), self.forcing, self.n)
            # the seed time is in the past: integrate from the scenario time at the seed
            self.sim_at_seed = sim_at(seed["ts"])
        elapsed = max(0.0, sim_at(real_now) - self.sim_at_seed)
        self.ens.advance_to(elapsed)
        h50, h90 = self.ens.hull(0.5), self.ens.hull(0.9)
        return {
            "seed_kind": seed["kind"], "seed_node": seed.get("node_id"), "seed_ts": seed["ts"],
            "seed": [loc.lat, loc.lon],
            "hull50": self.ens.hull_latlon(0.5), "hull90": self.ens.hull_latlon(0.9),
            "area50_m2": polygon_area(h50), "area90_m2": polygon_area(h90),
            "centroid": self.ens.centroid_latlon(),
            "sim_elapsed_s": elapsed, "multiplier": multiplier,
            "model": f"Leeway Monte Carlo, {self.ens.obj} (Allen & Plourde 1999), {self.n} particles",
            "forcing": self.forcing.label, "forcing_source": self.forcing.source,
            "forcing_default": self.forcing.is_default,
        }


def latlon_offset_m(a: LatLon, b: LatLon) -> tuple[float, float]:
    return latlon_to_enu(a, b)
