"""Ship deck camera: spawn native/aurora/aurora_bridge, parse frames, detect + track people, and
measure each person's depth for the rail trigger. Restarts the bridge if it exits."""
from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
import uuid
from pathlib import Path

import numpy as np

from ..config import ROOT
from ..perception.tracker import IoUTracker
from ..shipcam import box_depth_m, lateral_m

log = logging.getLogger("osprey.aurora")
BRIDGE = ROOT / "native/aurora/aurora_bridge"


class AuroraNode:
    node_id = "ship"

    def __init__(self, ground, mode: int = 2, flip: bool = False, jpeg_q: int = 75):
        self.g = ground
        self.mode, self.flip, self.jpeg_q = mode, flip, jpeg_q
        self.tracker = IoUTracker()
        self.session_id = "aurora-" + uuid.uuid4().hex[:6]
        self.proc = None
        self.status = "stopped"
        self.last_depth = None
        self.intrinsics = None
        self.restarts = 0
        self.timing = {"detect_ms": 0.0, "encode_ms": 0.0}

    @property
    def available(self) -> bool:
        return Path(BRIDGE).exists()

    async def run(self) -> None:
        while True:
            if self.g.sources.get("ship") != "aurora" or not self.available:
                self.status = "idle" if self.available else "bridge not built"
                await asyncio.sleep(0.5)
                continue
            try:
                await self._stream()
            except asyncio.CancelledError:
                await self._kill()
                raise
            except Exception:  # noqa: BLE001
                log.exception("aurora stream")
            await self._kill()
            self.restarts += 1
            self.status = f"restarting ({self.restarts})"
            await asyncio.sleep(1.0)

    async def _kill(self) -> None:
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 3)
            except asyncio.TimeoutError:
                self.proc.kill()
        self.proc = None

    async def _stream(self) -> None:
        self.status = "starting"
        self.proc = await asyncio.create_subprocess_exec(
            str(BRIDGE), str(self.mode), "80", "1" if self.flip else "0",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=4 << 20)
        self.session_id = "aurora-" + uuid.uuid4().hex[:6]
        rd = self.proc.stdout
        while self.g.sources.get("ship") == "aurora":
            n = struct.unpack("<I", await asyncio.wait_for(rd.readexactly(4), 5.0))[0]
            hdr = json.loads(await rd.readexactly(n))
            bgr_b = await rd.readexactly(hdr["bgr_len"])
            depth_b = await rd.readexactly(hdr["depth_len"]) if hdr["depth_len"] else b""
            # drop backlog: if more frames are already queued, skip to the newest
            if len(rd._buffer) > 2 * (n + hdr["bgr_len"] + hdr["depth_len"]):  # noqa: SLF001
                continue
            self.status = "streaming"
            await asyncio.to_thread(self._process, hdr, bgr_b, depth_b)

    def _process(self, hdr: dict, bgr_b: bytes, depth_b: bytes) -> None:
        import cv2

        w, h = hdr["w"], hdr["h"]
        bgr = np.frombuffer(bgr_b, np.uint8).reshape(h, w, 3)
        depth = np.frombuffer(depth_b, np.uint16).reshape(h, w) if depth_b else None
        self.last_depth = depth
        self.intrinsics = (hdr["fx"], hdr["fy"], hdr["cx"], hdr["cy"])
        t0 = time.perf_counter()
        ok, jpg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_q])
        self.timing["encode_ms"] = (time.perf_counter() - t0) * 1000
        dets = []
        det = self.g.detector
        if det is not None:
            t0 = time.perf_counter()
            dets = det.detect_rgb(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            self.timing["detect_ms"] = (time.perf_counter() - t0) * 1000
        capture_ts = hdr["ts_ms"] / 1000.0
        dets = self.tracker.update(capture_ts, dets)
        for d in dets:
            x1, y1, x2, y2 = d["bbox"]
            px = (int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h))
            z = box_depth_m(depth, px) if depth is not None else None
            d["z_m"] = z
            d["x_m"] = lateral_m((px[0] + px[2]) / 2, z, hdr["fx"], hdr["cx"]) if z else 0.0
        now = time.time()
        self.g.loop.call_soon_threadsafe(
            self.g.ingest_frame, "ship", jpg.tobytes(), self.session_id, hdr["seq"], capture_ts,
            now, "synced", dets, w, h, "aurora")

    def depth_at_center(self) -> dict:
        """Calibration helper: median depth in a central patch and per detected person."""
        d = self.last_depth
        if d is None:
            return {"ok": False}
        h, w = d.shape
        patch = d[h // 2 - 20:h // 2 + 20, w // 2 - 20:w // 2 + 20]
        v = patch[patch > 0]
        return {"ok": True, "center_m": float(np.median(v)) / 1000 if v.size else None,
                "valid_pct": float((d > 0).mean() * 100)}
