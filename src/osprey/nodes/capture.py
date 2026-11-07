"""Video captured on the Pi itself, for the FPV drone scout.

  usb  : a 5.8 GHz analog receiver with UVC output, or goggles' AV-out through a USB composite
         grabber. Both appear as a uvcvideo /dev/video* device; 'auto' picks the first one.
  file : replay of a recorded flight (e.g. the goggles' DVR .avi from the microSD card), paced
         at its own frame rate and looped. Labeled RECORDED in the UI; timestamps are replay time.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("osprey.capture")


def find_uvc_device() -> Optional[str]:
    base = Path("/sys/class/video4linux")
    if not base.exists():
        return None
    for d in sorted(base.iterdir(), key=lambda p: int(p.name.replace("video", "") or 0)):
        try:
            drv = os.path.basename(os.readlink(d / "device/driver"))
        except OSError:
            continue
        idx = (d / "index").read_text().strip() if (d / "index").exists() else "0"
        if drv == "uvcvideo" and idx == "0":  # index 0 = the capture node, not metadata
            return f"/dev/{d.name}"
    return None


def list_uvc() -> list[dict]:
    base = Path("/sys/class/video4linux")
    out = []
    if base.exists():
        for d in sorted(base.iterdir()):
            try:
                drv = os.path.basename(os.readlink(d / "device/driver"))
            except OSError:
                drv = "?"
            name = (d / "name").read_text().strip() if (d / "name").exists() else "?"
            out.append({"dev": f"/dev/{d.name}", "driver": drv, "name": name})
    return out


class CaptureNode:
    def __init__(self, ground, node_id: str, device: str = "auto", file: str = "",
                 fps: float = 12.0, jpeg_q: int = 75):
        self.g = ground
        self.node_id = node_id
        self.device, self.file = device, file
        self.fps, self.jpeg_q = fps, jpeg_q
        self.status = "idle"
        self.opened: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def mode(self) -> Optional[str]:
        src = self.g.sources.get(self.node_id)
        return src if src in ("usb", "file") else None

    def ensure(self) -> None:
        """Start the reader thread when the node's source is usb/file (called periodically)."""
        if self.mode() and (self._thread is None or not self._thread.is_alive()):
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name=f"capture-{self.node_id}",
                                            daemon=True)
            self._thread.start()

    def _open(self, mode: str):
        import cv2

        if mode == "file":
            path = os.path.expanduser(self.file)
            if not path or not os.path.exists(path):
                self.status = f"no file ({self.file or 'capture_file unset'})"
                return None, None
            return cv2.VideoCapture(path), path
        dev = find_uvc_device() if self.device == "auto" else self.device
        if dev is None:
            self.status = "no USB video device"
            return None, None
        cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap, dev

    def _run(self) -> None:
        import cv2

        from ..perception.tracker import IoUTracker

        tracker = IoUTracker()
        while not self._stop.is_set():
            mode = self.mode()
            if mode is None:
                self.status = "idle"
                return
            cap, name = self._open(mode)
            if cap is None or not cap.isOpened():
                time.sleep(1.0)
                continue
            self.opened = name
            session = f"{mode}-" + uuid.uuid4().hex[:6]
            src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            seq, last = 0, 0.0
            self.status = f"streaming {name}"
            while self.mode() == mode:
                t_read = time.time()
                ok, frame = cap.read()
                if not ok:
                    if mode == "file":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop the recording
                        continue
                    self.status = "read failed; reopening"
                    break
                if mode == "file":  # pace replay at the recording's frame rate
                    time.sleep(max(0.0, 1.0 / src_fps - (time.time() - t_read)))
                now = time.time()
                if now - last < 1.0 / self.fps:
                    continue  # process at most `fps` frames per second
                last = now
                if frame.shape[1] > 960:
                    frame = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
                h, w = frame.shape[:2]
                dets = tracker.update(now, self.g.detect(self.node_id, frame))
                ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_q])
                seq += 1
                self.g.loop.call_soon_threadsafe(
                    self.g.ingest_frame, self.node_id, jpg.tobytes(), session, seq, now, now,
                    "synced", dets, w, h, mode)
            cap.release()
        self.status = "stopped"
