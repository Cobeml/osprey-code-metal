"""Greedy IoU tracker: stable track ids across frames for one node."""
from __future__ import annotations

import itertools


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


class IoUTracker:
    def __init__(self, iou_min: float = 0.25, max_age_s: float = 0.7):
        self.iou_min = iou_min
        self.max_age_s = max_age_s
        self.tracks: dict[int, tuple[tuple, float]] = {}  # id -> (bbox, last_ts)
        self._ids = itertools.count(1)

    def update(self, ts: float, dets: list[dict]) -> list[dict]:
        """dets: [{bbox, confidence}] -> same dicts with track_id added."""
        self.tracks = {k: v for k, v in self.tracks.items() if ts - v[1] <= self.max_age_s}
        pairs = sorted(((iou(t[0], d["bbox"]), tid, i) for tid, t in self.tracks.items()
                        for i, d in enumerate(dets)), reverse=True)
        used_t, used_d = set(), set()
        for score, tid, i in pairs:
            if score < self.iou_min:
                break
            if tid in used_t or i in used_d:
                continue
            used_t.add(tid)
            used_d.add(i)
            dets[i]["track_id"] = tid
        for i, d in enumerate(dets):
            if i not in used_d:
                d["track_id"] = next(self._ids)
            self.tracks[d["track_id"]] = (tuple(d["bbox"]), ts)
        return dets
