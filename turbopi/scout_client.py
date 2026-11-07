#!/usr/bin/env python3
"""Scout A client for the Hiwonder TurboPi: camera -> Osprey (same binary WS protocol as the phone
page); follow/hold/stop commands -> pan-tilt servos.

Usage on the TurboPi:
  python3 scout_client.py wss://<tunnel>.trycloudflare.com [--camera 0] [--servo none|hiwonder]

Protocol: binary uint32 LE header_len | header JSON | JPEG, header {node_id, session_id, seq,
capture_ts_ms, width, height}; clock pings {"ping": ms} -> {"pong","srv"} -> {"sync","srv","recv"}.
Commands from the ground: {"type":"follow","err":[ex,ey]} (normalized box-center error),
{"type":"hold"}, {"type":"stop"}. The local loop keeps the person within +-15% of center with a
rate-limited P controller, and holds position when no command arrived for > 1 s.
"""
import argparse
import asyncio
import json
import struct
import time
import uuid

import cv2
import websockets

DEADBAND = 0.15
KP_DEG = 25.0        # degrees per unit normalized error per update
MAX_STEP_DEG = 3.0   # rate limit per update
STALE_S = 1.0


class NoServo:
    """Video-only scout (following not demonstrated)."""

    def __init__(self):
        self.pan, self.tilt = 0.0, 0.0

    def move(self, pan: float, tilt: float) -> None:
        self.pan, self.tilt = pan, tilt


class HiwonderServo(NoServo):
    """Pan-tilt via the Hiwonder SDK. Filled in after inspecting the TurboPi image (H3):
    the exact module and call are not known yet, so this raises until verified."""

    def __init__(self):
        super().__init__()
        raise NotImplementedError("inspect the TurboPi SDK first (Phase 7)")


class Follower:
    def __init__(self, servo, pan_limits=(-80, 80), tilt_limits=(-30, 45)):
        self.servo = servo
        self.pan_limits, self.tilt_limits = pan_limits, tilt_limits
        self.last_cmd = 0.0
        self.mode = "stop"

    def command(self, m: dict) -> None:
        self.mode = m.get("type", "stop")
        self.last_cmd = time.time()
        if self.mode == "follow":
            ex, ey = m["err"]
            dp = self._step(ex)
            dt = self._step(ey)
            pan = min(max(self.servo.pan - dp, self.pan_limits[0]), self.pan_limits[1])
            tilt = min(max(self.servo.tilt - dt, self.tilt_limits[0]), self.tilt_limits[1])
            self.servo.move(pan, tilt)

    @staticmethod
    def _step(e: float) -> float:
        if abs(e) <= DEADBAND / 2:
            return 0.0
        return max(-MAX_STEP_DEG, min(MAX_STEP_DEG, KP_DEG * e))

    @property
    def state(self) -> str:
        if self.mode == "follow" and time.time() - self.last_cmd > STALE_S:
            return "hold (stale)"
        return self.mode


async def run(url: str, cam_index: int, servo, fps: float = 10.0):
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    follower = Follower(servo)
    session = "turbopi-" + uuid.uuid4().hex[:6]
    seq = 0
    ws_url = url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://") + "/ws/scout?node=A"
    while True:
        try:
            async with websockets.connect(ws_url, max_size=None, ping_interval=5) as ws:
                print("connected", ws_url)

                async def receiver():
                    async for msg in ws:
                        m = json.loads(msg)
                        if "pong" in m:
                            await ws.send(json.dumps({"sync": m["pong"], "srv": m["srv"], "recv": time.time() * 1000}))
                        elif m.get("type") in ("follow", "hold", "stop"):
                            follower.command(m)

                async def pinger():
                    while True:
                        await ws.send(json.dumps({"ping": time.time() * 1000}))
                        await asyncio.sleep(1.0)

                tasks = [asyncio.create_task(receiver()), asyncio.create_task(pinger())]
                period = 1.0 / fps
                try:
                    while True:
                        t0 = time.time()
                        ok, frame = await asyncio.to_thread(cap.read)
                        if not ok:
                            await asyncio.sleep(0.2)
                            continue
                        ts = time.time() * 1000
                        h, w = frame.shape[:2]
                        ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        seq += 1
                        hdr = json.dumps({"node_id": "A", "session_id": session, "seq": seq,
                                          "capture_ts_ms": ts, "width": w, "height": h}).encode()
                        await ws.send(struct.pack("<I", len(hdr)) + hdr + jpg.tobytes())
                        await asyncio.sleep(max(0.0, period - (time.time() - t0)))
                finally:
                    for t in tasks:
                        t.cancel()
        except Exception as e:  # noqa: BLE001
            print("link error:", e, "- retrying in 1 s")
            await asyncio.sleep(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--servo", default="none", choices=["none", "hiwonder"])
    a = ap.parse_args()
    servo = HiwonderServo() if a.servo == "hiwonder" else NoServo()
    asyncio.run(run(a.url, a.camera, servo))


if __name__ == "__main__":
    main()
