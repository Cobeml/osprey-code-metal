"""Green target vs red decoy classification (ground and rover share perception/ballcolor.py)."""
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")  # the Mac venv has no OpenCV; these run on the Pi

from osprey.perception import ballcolor
from osprey.perception.targets import detect_targets, is_target, merge

W, H = 640, 480
GREEN = (0, 200, 0)        # BGR, hue 60
RED = (0, 0, 220)          # BGR, hue 0
RED_WRAP = (60, 0, 220)    # BGR, hue ~172: the other end of the red band
SEA = (120, 90, 40)        # dull blue-grey background, matches neither colour


def scene(*balls):
    img = np.full((H, W, 3), SEA, np.uint8)
    for (cx, cy, r, col) in balls:
        cv2.circle(img, (cx, cy), r, col, -1)
    return img


def nbox(cx, cy, r):
    return ((cx - r) / W, (cy - r) / H, (cx + r) / W, (cy + r) / H)


@pytest.mark.parametrize("col,label", [(GREEN, "green"), (RED, "red"), (RED_WRAP, "red"),
                                       ((128, 128, 128), "unknown")])
def test_classify_box(col, label):
    img = scene((320, 240, 40, col))
    got, _ = ballcolor.classify_box(img, nbox(320, 240, 40))
    assert got == label


def test_blobs_find_both_colours():
    img = scene((150, 240, 30, GREEN), (480, 240, 30, RED))
    res = ballcolor.find_balls(img)
    assert res["target"] is not None and res["target"]["bbox"][0] < 0.5
    assert len(res["decoys"]) == 1 and res["decoys"][0]["bbox"][0] > 0.5


def test_red_alone_is_never_a_target():
    res = ballcolor.find_balls(scene((320, 240, 35, RED)))
    assert res["target"] is None and len(res["decoys"]) == 1


def test_detect_targets_without_network_labels_and_filters():
    dets = detect_targets("ball", scene((150, 240, 30, GREEN), (480, 240, 30, RED_WRAP)), None)
    cls = sorted(d["cls"] for d in dets)
    assert cls == ["green", "red"]
    assert [d["cls"] for d in dets if is_target(d)] == ["green"]


class FakeDetector:
    """Stands in for Hailo: proposes colour-blind 'sports ball' boxes."""

    def __init__(self, boxes):
        self.boxes = boxes

    def detect_rgb(self, rgb, classes):
        return [{"bbox": b, "confidence": 0.99, "cls": "ball"} for b in self.boxes]


def test_network_ball_boxes_get_colour_labels():
    img = scene((150, 240, 30, GREEN), (480, 240, 30, RED))
    det = FakeDetector([nbox(150, 240, 30), nbox(480, 240, 30)])
    dets = detect_targets("ball", img, det)
    by_x = sorted(dets, key=lambda d: d["bbox"][0])
    assert [d["cls"] for d in by_x] == ["green", "red"]


def test_unknown_colour_ball_is_not_a_target():
    img = scene((320, 240, 40, (128, 128, 128)))
    dets = detect_targets("ball", img, FakeDetector([nbox(320, 240, 40)]))
    assert len(dets) == 1 and dets[0]["cls"] == "ball" and not is_target(dets[0])


def test_merge_prefers_colour_label_over_unknown():
    unknown = {"bbox": (0.1, 0.1, 0.3, 0.3), "confidence": 0.99, "cls": "ball"}
    green = {"bbox": (0.11, 0.1, 0.31, 0.3), "confidence": 0.6, "cls": "green"}
    assert merge([unknown, green]) == [green]


def test_sim_detections_without_cls_stay_targets():
    assert is_target({"bbox": (0, 0, 1, 1), "confidence": 0.9})
