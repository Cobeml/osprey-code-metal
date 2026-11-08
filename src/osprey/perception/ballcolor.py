"""Ball colour classifier: green = target (person in the water), red = decoy.

Pure OpenCV + NumPy with no other osprey imports, so the TurboPi's onboard Pi can run the exact
same code as the ground processor (turbopi/scout_client.py imports this file).

Colours are thresholded in OpenCV HSV (H 0-179, S/V 0-255). Red wraps around hue 0, so it needs
two hue bands. All thresholds are starting points: tune them at the venue under its lighting
(phone exposure/white balance should be locked).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

TARGET = "green"
DECOY = "red"
UNKNOWN = "unknown"

# (lo, hi) HSV bands per colour
GREEN_BANDS: tuple = (((35, 80, 50), (85, 255, 255)),)
RED_BANDS: tuple = (((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (179, 255, 255)))

MIN_COLOR_FRAC = 0.25      # share of a box's inner pixels that must match for a colour label
INNER_FRAC = 0.6           # classify on the central part of the box (drops background corners)
MIN_AREA_FRAC = 0.0004     # blob size limits, as a fraction of the frame
MAX_AREA_FRAC = 0.25
MIN_ASPECT = 0.5           # roundish: short side / long side
MIN_FILL = 0.45            # contour area / box area (a disc fills ~0.785)
DISC_FILL = 0.785
MAX_CONF = 0.95
MORPH_KERNEL = 5


def bands_for(color: str, green=GREEN_BANDS, red=RED_BANDS) -> tuple:
    if color == TARGET:
        return green
    if color == DECOY:
        return red
    raise ValueError(f"unknown colour {color!r}")


def color_mask(hsv: np.ndarray, bands: tuple) -> np.ndarray:
    import cv2

    mask = np.zeros(hsv.shape[:2], np.uint8)
    for lo, hi in bands:
        mask |= cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
    return mask


def color_blobs(bgr: np.ndarray, color: str, bands: Optional[tuple] = None,
                hsv: Optional[np.ndarray] = None) -> list[dict]:
    """Roundish saturated blobs of one colour. Normalized boxes, shape-based confidence."""
    import cv2

    h, w = bgr.shape[:2]
    if hsv is None:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = color_mask(hsv, bands or bands_for(color))
    k = np.ones((MORPH_KERNEL, MORPH_KERNEL), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (MIN_AREA_FRAC * w * h <= area <= MAX_AREA_FRAC * w * h):
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = min(bw, bh) / max(bw, bh)
        fill = area / float(bw * bh)
        if aspect < MIN_ASPECT or fill < MIN_FILL:
            continue
        conf = float(min(MAX_CONF, 0.4 + 0.35 * aspect + 0.25 * min(1.0, fill / DISC_FILL)))
        out.append({"bbox": (x / w, y / h, (x + bw) / w, (y + bh) / h), "confidence": conf,
                    "cls": color})
    return out


def classify_box(bgr: np.ndarray, bbox: tuple, green=GREEN_BANDS, red=RED_BANDS,
                 hsv: Optional[np.ndarray] = None) -> tuple[str, float]:
    """Label a (normalized) box green / red / unknown by the share of matching inner pixels."""
    import cv2

    h, w = bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    mx, my = (1 - INNER_FRAC) / 2 * (x2 - x1), (1 - INNER_FRAC) / 2 * (y2 - y1)
    c1, c2 = max(0, int((x1 + mx) * w)), min(w, int(np.ceil((x2 - mx) * w)))
    r1, r2 = max(0, int((y1 + my) * h)), min(h, int(np.ceil((y2 - my) * h)))
    if c2 <= c1 or r2 <= r1:
        return UNKNOWN, 0.0
    crop = (hsv if hsv is not None else cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV))[r1:r2, c1:c2]
    n = float(crop.shape[0] * crop.shape[1])
    g = float(np.count_nonzero(color_mask(crop, green))) / n
    r = float(np.count_nonzero(color_mask(crop, red))) / n
    best, frac = (TARGET, g) if g >= r else (DECOY, r)
    return (best, frac) if frac >= MIN_COLOR_FRAC else (UNKNOWN, max(g, r))


def find_balls(bgr: np.ndarray, green=GREEN_BANDS, red=RED_BANDS) -> dict:
    """Onboard helper: best green target box (or None), every green box, and the red decoys."""
    import cv2

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    greens = color_blobs(bgr, TARGET, green, hsv)
    reds = color_blobs(bgr, DECOY, red, hsv)
    target = max(greens, key=lambda d: d["confidence"]) if greens else None
    return {"target": target, "greens": greens, "decoys": reds}
