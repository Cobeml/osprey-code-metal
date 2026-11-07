"""Local tangent-plane geometry. ENU: x east, y north, meters, relative to an origin lat/lon.

Flat-earth approximation is accurate to well under a meter over the few-km demo area.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

R_EARTH = 6_371_008.8  # mean Earth radius, m


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


def enu_to_latlon(origin: LatLon, x: float, y: float) -> LatLon:
    lat = origin.lat + math.degrees(y / R_EARTH)
    lon = origin.lon + math.degrees(x / (R_EARTH * math.cos(math.radians(origin.lat))))
    return LatLon(lat, lon)


def latlon_to_enu(origin: LatLon, p: LatLon) -> tuple[float, float]:
    y = math.radians(p.lat - origin.lat) * R_EARTH
    x = math.radians(p.lon - origin.lon) * R_EARTH * math.cos(math.radians(origin.lat))
    return x, y


def horizontal_distance_m(a: LatLon, b: LatLon) -> float:
    """Haversine distance in meters."""
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(h)))


def offset_by_bearing(origin: LatLon, bearing_deg: float, dist_m: float) -> LatLon:
    b = math.radians(bearing_deg)
    return enu_to_latlon(origin, dist_m * math.sin(b), dist_m * math.cos(b))


@dataclass(frozen=True)
class ShipPose:
    """Configured (simulated) ship position. heading: degrees true, clockwise from north.
    cam_bearing_rel: camera optical axis relative to the bow (90 = looking out to starboard)."""

    lat: float
    lon: float
    heading_deg: float = 45.0
    cam_bearing_rel: float = 90.0

    @property
    def origin(self) -> LatLon:
        return LatLon(self.lat, self.lon)

    def camera_point(self, x_right_m: float, z_fwd_m: float) -> LatLon:
        """Camera-frame (X right, Z forward, horizontal) to lat/lon via the ship pose."""
        bf = math.radians(self.heading_deg + self.cam_bearing_rel)
        br = bf + math.pi / 2
        east = z_fwd_m * math.sin(bf) + x_right_m * math.sin(br)
        north = z_fwd_m * math.cos(bf) + x_right_m * math.cos(br)
        return enu_to_latlon(self.origin, east, north)
