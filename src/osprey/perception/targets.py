"""What each node looks for.

  person : Hailo yolov8s COCO 'person'
  ball   : the demo's person-in-water stand-in (a green foam ball): Hailo COCO 'sports ball'
           united with an HSV green-blob detector (tunable thresholds; the UI labels the target)
Detections from both sources are merged by IoU, keeping the higher confidence.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .detector import PERSON, SPORTS_BALL
from .tracker import iou


def green_blobs(bgr: np.ndarray, lo=(35, 80, 50), hi=(85, 255, 255),
                min_area_frac: float = 0.0004, max_area_frac: float = 0.25) -> list[dict]:
    """Roundish saturated-green blobs. Returns normalized boxes with a shape-based confidence."""
    import cv2

    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
    k = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (min_area_frac * w * h <= area <= max_area_frac * w * h):
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = min(bw, bh) / max(bw, bh)
        fill = area / float(bw * bh)  # a disc fills ~0.785 of its box
        if aspect < 0.5 or fill < 0.45:
            continue
        conf = float(min(0.95, 0.4 + 0.35 * aspect + 0.25 * min(1.0, fill / 0.785)))
        out.append({"bbox": (x / w, y / h, (x + bw) / w, (y + bh) / h), "confidence": conf,
                    "cls": "green"})
    return out


def merge(dets: list[dict], thr: float = 0.3) -> list[dict]:
    kept: list[dict] = []
    for d in sorted(dets, key=lambda d: -d["confidence"]):
        if all(iou(d["bbox"], k["bbox"]) < thr for k in kept):
            kept.append(d)
    return kept


def detect_targets(target: str, bgr: Optional[np.ndarray], detector, hsv=None) -> list[dict]:
    """target: 'person', 'ball' or 'person+ball'."""
    if bgr is None:
        return []
    import cv2

    want = set(target.split("+"))
    classes = tuple(c for name, c in (("person", PERSON), ("ball", SPORTS_BALL)) if name in want)
    dets: list[dict] = []
    if detector is not None and classes:
        dets += detector.detect_rgb(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), classes)
    if "ball" in want:
        lo, hi = (hsv or ((35, 80, 50), (85, 255, 255)))
        dets += green_blobs(bgr, lo, hi)
    return merge(dets)
