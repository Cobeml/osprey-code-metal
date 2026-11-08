"""What each node looks for.

  person : Hailo yolov8s COCO 'person'
  ball   : the demo's person-in-water stand-in is a GREEN foam ball; a RED ball is a decoy.
           Hailo COCO 'sports ball' proposes balls of any colour and each box is labelled by
           colour (perception/ballcolor.py); HSV green and red blob detectors catch balls the
           network misses. Output cls: 'green' (target), 'red' (decoy, never a candidate),
           'ball' (colour unknown, not a target either).
Detections from all sources are merged by IoU. Colour-labelled boxes win over colour-unknown
ones, then higher confidence wins.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from . import ballcolor
from .detector import PERSON, SPORTS_BALL
from .tracker import iou

UNKNOWN_BALL = "ball"
DECOY_CLASSES = frozenset({ballcolor.DECOY, UNKNOWN_BALL})


def green_blobs(bgr: np.ndarray, lo=(35, 80, 50), hi=(85, 255, 255)) -> list[dict]:
    """Kept for callers of the old API."""
    return ballcolor.color_blobs(bgr, ballcolor.TARGET, ((lo, hi),))


def merge(dets: list[dict], thr: float = 0.3) -> list[dict]:
    kept: list[dict] = []
    for d in sorted(dets, key=lambda d: (d.get("cls") == UNKNOWN_BALL, -d["confidence"])):
        if all(iou(d["bbox"], k["bbox"]) < thr for k in kept):
            kept.append(d)
    return kept


def is_target(d: dict) -> bool:
    """Sim detections carry no cls and are targets; red decoys and unknown-colour balls are not."""
    return d.get("cls") not in DECOY_CLASSES


def detect_targets(target: str, bgr: Optional[np.ndarray], detector, hsv=None,
                   red_bands: Optional[tuple] = None) -> list[dict]:
    """target: 'person', 'ball' or 'person+ball'. hsv: (lo, hi) for green."""
    if bgr is None:
        return []
    import cv2

    want = set(target.split("+"))
    green = ((tuple(hsv[0]), tuple(hsv[1])),) if hsv else ballcolor.GREEN_BANDS
    red = red_bands or ballcolor.RED_BANDS
    classes = tuple(c for name, c in (("person", PERSON), ("ball", SPORTS_BALL)) if name in want)
    dets: list[dict] = []
    if detector is not None and classes:
        dets += detector.detect_rgb(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), classes)
    if "ball" in want:
        hsv_img = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        for d in dets:
            if d.get("cls") == UNKNOWN_BALL:
                label, frac = ballcolor.classify_box(bgr, d["bbox"], green, red, hsv_img)
                d["cls"] = UNKNOWN_BALL if label == ballcolor.UNKNOWN else label
                d["color_frac"] = round(frac, 2)
        dets += ballcolor.color_blobs(bgr, ballcolor.TARGET, green, hsv_img)
        dets += ballcolor.color_blobs(bgr, ballcolor.DECOY, red, hsv_img)
    return merge(dets)
