"""Person detector: Hailo-8 yolov8s_h8.hef (on-chip NMS) with a letterboxed 640x640 input.

One shared VDevice for all nodes; inference is serialized on one worker thread. Output with
FLOAT32 NMS-by-class: per class an (n, 5) array [ymin, xmin, ymax, xmax, score], normalized to the
model input. Person is COCO class 0.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import numpy as np

PERSON = 0


def letterbox(img: np.ndarray, size: int = 640) -> tuple[np.ndarray, float, int, int]:
    import cv2

    h, w = img.shape[:2]
    s = min(size / w, size / h)
    nw, nh = int(round(w * s)), int(round(h * s))
    out = np.full((size, size, 3), 114, np.uint8)
    px, py = (size - nw) // 2, (size - nh) // 2
    out[py:py + nh, px:px + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return out, s, px, py


class HailoDetector:
    """All HailoRT calls run on one dedicated thread: vstreams created on one thread and used from
    another block inside infer() while holding the GIL, which freezes the whole process."""

    def __init__(self, hef_path: str, score: float = 0.45):
        from concurrent.futures import ThreadPoolExecutor

        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hailo")
        self._pool.submit(self._init, hef_path, score).result()

    def _init(self, hef_path: str, score: float) -> None:
        from hailo_platform import (HEF, ConfigureParams, FormatType, HailoSchedulingAlgorithm,
                                    HailoStreamInterface, InferVStreams, InputVStreamParams,
                                    OutputVStreamParams, VDevice)

        self.score = score
        self.hef = HEF(hef_path)
        params = VDevice.create_params()
        params.scheduling_algorithm = HailoSchedulingAlgorithm.NONE
        self.vdev = VDevice(params)
        cfg = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
        self.ng = self.vdev.configure(self.hef, cfg)[0]
        self.ivp = InputVStreamParams.make(self.ng, format_type=FormatType.UINT8)
        self.ovp = OutputVStreamParams.make(self.ng, format_type=FormatType.FLOAT32)
        self.in_name = self.hef.get_input_vstream_infos()[0].name
        self.out_name = self.hef.get_output_vstream_infos()[0].name
        self._activation = self.ng.activate(self.ng.create_params())
        self._activation.__enter__()
        self._pipe = InferVStreams(self.ng, self.ivp, self.ovp)
        self._pipe.__enter__()
        self.lock = threading.Lock()
        self.last_ms = 0.0

    def detect_rgb(self, rgb: np.ndarray) -> list[dict]:
        """rgb: HxWx3 uint8 RGB. Returns [{bbox (normalized x1,y1,x2,y2 of the input image), confidence}]."""
        h, w = rgb.shape[:2]
        lb, s, px, py = letterbox(rgb)
        t0 = time.perf_counter()
        out = self._pool.submit(self._infer, lb).result()
        self.last_ms = (time.perf_counter() - t0) * 1000
        dets = []
        persons = out[0][PERSON]
        for ymin, xmin, ymax, xmax, sc in np.asarray(persons).reshape(-1, 5):
            if sc < self.score:
                continue
            x1 = (xmin * 640 - px) / s / w
            x2 = (xmax * 640 - px) / s / w
            y1 = (ymin * 640 - py) / s / h
            y2 = (ymax * 640 - py) / s / h
            dets.append({"bbox": (float(max(0.0, x1)), float(max(0.0, y1)),
                                  float(min(1.0, x2)), float(min(1.0, y2))),
                         "confidence": float(sc)})
        return dets

    def _infer(self, lb: np.ndarray):
        return self._pipe.infer({self.in_name: lb[None]})[self.out_name]

    def detect_jpeg(self, jpeg: bytes) -> tuple[list[dict], Optional[np.ndarray]]:
        import cv2

        bgr = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            return [], None
        return self.detect_rgb(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), bgr

    def close(self) -> None:
        self._pool.submit(self._close).result()

    def _close(self) -> None:
        try:
            self._pipe.__exit__(None, None, None)
            self._activation.__exit__(None, None, None)
        finally:
            self.vdev.release()


def make_detector(kind: str, hef_path: str):
    if kind != "hailo":
        return None
    try:
        return HailoDetector(hef_path)
    except Exception as e:  # noqa: BLE001
        import logging

        logging.getLogger("osprey").warning("Hailo detector unavailable: %r", e)
        return None


if __name__ == "__main__":
    import sys

    import cv2

    det = HailoDetector(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/hailo-models/yolov8s_h8.hef")
    img = cv2.imread(sys.argv[2]) if len(sys.argv) > 2 else np.zeros((400, 640, 3), np.uint8)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    det.detect_rgb(rgb)
    t0 = time.perf_counter()
    n = 50
    for _ in range(n):
        d = det.detect_rgb(rgb)
    dt = time.perf_counter() - t0
    print(f"{n / dt:.1f} fps end-to-end (letterbox+infer), infer {det.last_ms:.1f} ms; dets={d}")
    det.close()
