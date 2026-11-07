"""Synthetic nodes for development, tests and demo fallback. Every frame is labeled SIM."""
from __future__ import annotations

import io
import math
import time
import uuid
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..shipcam import lateral_m

W, H = 640, 400


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


FONT = _font(16)
FONT_BIG = _font(22)


def _jpeg(img: Image.Image, q: int = 70) -> bytes:
    b = io.BytesIO()
    img.save(b, "JPEG", quality=q)
    return b.getvalue()


def _stamp(d: ImageDraw.ImageDraw, label: str, now: float) -> None:
    ts = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int(now * 1000) % 1000:03d}"
    d.rectangle([0, 0, W, 26], fill=(0, 0, 0))
    d.text((8, 4), f"SIM  {label}", fill=(255, 200, 0), font=FONT)
    d.text((W - 120, 4), ts, fill=(255, 255, 255), font=FONT)


class SimShipCam:
    """Deck camera view: deck floor, rail line, one crew member who can walk over the rail."""

    node_id = "ship"

    def __init__(self, rail_m: float, cam_h: float, fx: float, fy: float, cx: float, cy: float,
                 tilt_deg: float = 30.0):
        self.tilt = math.radians(tilt_deg)
        self.session_id = "sim-" + uuid.uuid4().hex[:6]
        self.seq = 0
        self.rail_m, self.cam_h, self.fx, self.fy, self.cx, self.cy = rail_m, cam_h, fx, fy, cx, cy
        self.walk_t0: Optional[float] = None
        self.track_id = 1
        self._bg = self._background()

    def project(self, x: float, z: float, y_world: float) -> tuple[float, float]:
        """Pixel (u, v) of a point x right, z ahead (horizontal), y_world above the floor,
        for a camera at cam_h tilted down by `tilt`."""
        dy = self.cam_h - y_world
        zc = z * math.cos(self.tilt) + dy * math.sin(self.tilt)
        yc = dy * math.cos(self.tilt) - z * math.sin(self.tilt)
        return self.cx + self.fx * x / zc, self.cy + self.fy * yc / zc

    def row_for_depth(self, z: float) -> float:
        return self.project(0.0, z, 0.0)[1]

    def _background(self) -> Image.Image:
        img = Image.new("RGB", (W, H), (40, 70, 110))
        d = ImageDraw.Draw(img)
        rail_row = self.row_for_depth(self.rail_m)
        for y in range(int(rail_row), H):
            g = int(90 + 60 * (y - rail_row) / max(1, H - rail_row))
            d.line([(0, y), (W, y)], fill=(g, g, g - 10))
        for k in range(1, 6):  # sea texture beyond the rail
            y = int(rail_row - k * 14)
            d.line([(0, y), (W, y + 4)], fill=(60, 95, 140), width=2)
        d.line([(0, rail_row), (W, rail_row)], fill=(255, 220, 0), width=3)
        d.text((8, rail_row - 22), f"RAIL {self.rail_m:.2f} m", fill=(255, 220, 0), font=FONT)
        return img

    def start_crossing(self, now: float) -> None:
        if self.walk_t0 is None:
            self.walk_t0 = now
            self.track_id += 1

    def reset(self) -> None:
        """After End Incident a crew member is back on deck."""
        self.walk_t0 = None
        self.track_id += 1

    def person(self, now: float) -> Optional[tuple[float, float]]:
        """(X, Z) of the crew member in camera coordinates, or None when out of view."""
        if self.walk_t0 is None:
            return 0.15 + 0.1 * math.sin(now * 0.7), 1.15 + 0.05 * math.sin(now * 1.3)
        t = now - self.walk_t0
        if t < 2.5:  # walk from 1.15 m to 2.4 m (beyond the rail)
            return 0.15 + 0.1 * t, 1.15 + 1.25 * t / 2.5
        if t < 3.2:
            return 0.4, 2.4 + 0.3 * (t - 2.5)
        return None  # gone over the side

    def frame(self, now: float) -> tuple[bytes, list[dict]]:
        self.seq += 1
        img = self._bg.copy()
        d = ImageDraw.Draw(img)
        dets = []
        p = self.person(now)
        if p is not None:
            x, z = p
            cxp, top = self.project(x, z, 1.75)
            _, bot = self.project(x, z, 0.0)
            hw = (self.project(x + 0.25, z, 0.9)[0] - self.project(x - 0.25, z, 0.9)[0]) / 2
            d.rectangle([cxp - hw, top + (bot - top) * 0.18, cxp + hw, bot], fill=(200, 60, 30))
            d.ellipse([cxp - hw * 0.5, top, cxp + hw * 0.5, top + (bot - top) * 0.18], fill=(230, 180, 140))
            bb = (max(0, cxp - hw) / W, max(0, top) / H, min(W, cxp + hw) / W, min(H, bot) / H)
            dets.append({"track_id": self.track_id, "bbox": bb, "confidence": 0.93, "z_m": z,
                         "x_m": lateral_m(cxp, z, self.fx, self.cx)})
        _stamp(d, "Ship deck camera (no Aurora)", now)
        return _jpeg(img), dets


class SimScout:
    """Overhead view of the sea; the person (orange life vest) appears when visible."""

    def __init__(self, node_id: str, label: str, seed: int):
        self.node_id = node_id
        self.label = label
        self.session_id = "sim-" + uuid.uuid4().hex[:6]
        self.seq = 0
        self.rng = np.random.default_rng(seed)
        self.pos = np.array([0.7, 0.3])
        self.vel = np.zeros(2)
        self.track_id = 0
        self.was_visible = False
        self.textures = [self._sea(i) for i in range(4)]

    def _sea(self, k: int) -> Image.Image:
        rng = np.random.default_rng(100 + k)
        base = np.zeros((H, W, 3), np.uint8)
        yy, xx = np.mgrid[0:H, 0:W]
        wave = (np.sin(xx / 23.0 + k * 0.8 + yy / 41.0) + np.sin(yy / 17.0 - k * 0.6)) * 8
        noise = rng.normal(0, 5, (H, W))
        v = wave + noise
        base[..., 0] = np.clip(20 + v, 0, 255)
        base[..., 1] = np.clip(70 + v, 0, 255)
        base[..., 2] = np.clip(105 + v * 1.4, 0, 255)
        return Image.fromarray(base)

    def frame(self, now: float, visible: bool, following: bool) -> tuple[bytes, list[dict]]:
        self.seq += 1
        img = self.textures[(self.seq // 3) % len(self.textures)].copy()
        d = ImageDraw.Draw(img)
        dets = []
        if visible:
            if not self.was_visible:
                self.track_id += 1
                self.pos = np.array([self.rng.uniform(0.2, 0.8), self.rng.uniform(0.25, 0.75)])
            self.vel = 0.85 * self.vel + self.rng.normal(0, 0.004, 2)
            if following:  # camera keeps the person in the central region
                self.vel += (np.array([0.5, 0.5]) - self.pos) * 0.08
            self.pos = np.clip(self.pos + self.vel, 0.08, 0.92)
            cx, cy = self.pos[0] * W, self.pos[1] * H
            r = 16
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 120, 0))
            d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(225, 175, 135))
            d.arc([cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10], 0, 360, fill=(220, 235, 245), width=2)
            bb = ((cx - r - 4) / W, (cy - r - 4) / H, (cx + r + 4) / W, (cy + r + 4) / H)
            dets.append({"track_id": self.track_id, "bbox": bb,
                         "confidence": float(0.80 + 0.15 * self.rng.random())})
        self.was_visible = visible
        _stamp(d, self.label, now)
        return _jpeg(img), dets
