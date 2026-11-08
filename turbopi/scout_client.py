#!/usr/bin/env python3
"""Rover scout client for the Hiwonder TurboPi: camera -> Osprey (same binary WS protocol as the
phone page); dispatch/follow/hold/stop commands -> chassis + pan-tilt.

Usage on the TurboPi:
  python3 scout_client.py wss://<tunnel>.trycloudflare.com [--node B] [--camera 0] [--hw none|hiwonder]

Dispatch flow (rover starts beside the deck camera, facing along its optical axis):
  {"type":"dispatch","heading_deg","distance_m"} -> turn to heading, drive the distance (timed,
  no wheel encoders) -> "searching": rotate slowly while the ground looks for the target in this
  camera -> once the ground associates the target it sends follow errors -> "approaching": turn
  toward the box and creep forward until the box is big enough -> "arrived" (stop).
  Every state change is reported as {"type":"rover_state","state":...,"onboard":{...}}.

Onboard check (--onboard): "green" (default) runs the ground's green/red ball classifier
(src/osprey/perception/ballcolor.py; copy it next to this file or run from the repo); "person"
runs OpenCV's HOG people detector on the rover's own Pi (no Hailo there); "none" means ground
guidance only. While the link is up but the ground has no fresh follow error, the
rover steers on its own onboard sighting (red balls never steer it). Ground follow errors take
priority, stop always wins, and the rover still stops if the link drops.

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
import sys
import time
import uuid
from pathlib import Path

import websockets


def _load_ballcolor():
    """Same classifier as the ground: next to this file, installed osprey, or the repo's src/."""
    here = Path(__file__).resolve().parent
    for p in (here, here.parent / "src"):
        if str(p) not in sys.path:
            sys.path.append(str(p))
    try:
        import ballcolor  # copied next to this file on the rover
        return ballcolor
    except ImportError:
        pass
    try:
        from osprey.perception import ballcolor
        return ballcolor
    except ImportError:
        return None


ballcolor = _load_ballcolor()

DEADBAND = 0.15
KP_DEG = 25.0        # degrees per unit normalized error per update
MAX_STEP_DEG = 3.0   # rate limit per update
STALE_S = 1.0


class NoHardware:
    """Video-only scout: prints what it would do (following not demonstrated)."""

    def __init__(self):
        self.pan, self.tilt = 0.0, 0.0

    def move(self, pan: float, tilt: float) -> None:
        self.pan, self.tilt = pan, tilt

    def drive(self, forward: float, turn: float) -> None:
        """forward in [-1, 1] (fraction of max speed), turn in [-1, 1] (+ = clockwise)."""
        print(f"drive forward={forward:+.2f} turn={turn:+.2f}")

    def stop(self) -> None:
        print("stop")


class HiwonderHardware(NoHardware):
    """Chassis + pan-tilt through the Hiwonder SDK. Filled in after inspecting the TurboPi image
    (H3); the exact modules and calls are not known yet, so this raises until verified."""

    def __init__(self):
        super().__init__()
        raise NotImplementedError("inspect the TurboPi SDK first (Phase 7)")


# timed dead reckoning (calibrate on the floor at the venue)
DRIVE_SPEED = 0.5         # fraction of max
DRIVE_M_PER_S = 0.25      # measured ground speed at DRIVE_SPEED
TURN_DEG_PER_S = 90.0     # measured spin rate at turn=0.5
SEARCH_TURN = 0.25
ARRIVE_BOX_H = 0.85       # target box height (fraction of frame) that counts as "arrived"
ARRIVE_BY_TARGET = {"person": 0.85, "green": 0.45, "none": 0.85}


class PersonHOG:
    """OpenCV's built-in HOG + linear SVM people detector: no model files, CPU only."""

    def __init__(self, width: int = 320):
        import cv2

        self.cv2 = cv2
        self.width = width
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def best(self, frame):
        cv2 = self.cv2
        h, w = frame.shape[:2]
        s = self.width / float(w)
        small = cv2.resize(frame, (self.width, int(h * s)))
        rects, weights = self.hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
        if len(rects) == 0:
            return None
        i = int(max(range(len(rects)), key=lambda k: float(weights[k])))
        x, y, bw, bh = rects[i]
        sh, sw = small.shape[:2]
        conf = float(min(0.99, max(0.0, 0.5 + 0.25 * float(weights[i]))))
        return {"bbox": (x / sw, y / sh, (x + bw) / sw, (y + bh) / sh), "confidence": conf}


class Rover:
    """Dispatch state machine. tick() runs ~10 Hz."""

    def __init__(self, hw, report):
        self.hw, self.report = hw, report
        self.state = "idle"
        self.until = 0.0
        self.plan = None
        self.follow = None  # last follow message
        self.follow_ts = 0.0
        self.local = None   # onboard green-ball sighting, same shape as a follow message
        self.local_ts = 0.0
        self.decoys = 0     # red balls in the last onboard frame
        self.guide_src = None

    def on_local(self, target, decoys: int = 0) -> None:
        """Onboard classifier result for one frame (target: {"bbox","confidence"} or None)."""
        self.decoys = decoys
        if target is None:
            return
        x1, y1, x2, y2 = target["bbox"]
        self.local = {"err": [(x1 + x2) / 2 - 0.5, (y1 + y2) / 2 - 0.5], "size": y2 - y1,
                      "confidence": target["confidence"]}
        self.local_ts = time.time()

    def onboard(self) -> dict:
        """What the rover's own camera says, reported with every state change."""
        fresh = self.local is not None and time.time() - self.local_ts <= STALE_S
        label = getattr(self, "onboard_label", "green")
        return {"label": label if fresh else None, "color": "green" if fresh and label == "green" else None,
                "confidence": round(self.local["confidence"], 2) if fresh else None,
                "decoys": self.decoys, "guide": self.guide_src,
                "classifier": ballcolor is not None}

    def _guide(self, now: float):
        """Ground follow error first, then the onboard green sighting, else None."""
        if self.follow is not None and now - self.follow_ts <= STALE_S:
            self.guide_src = "ground"
            return self.follow
        if self.local is not None and now - self.local_ts <= STALE_S:
            self.guide_src = "onboard"
            return self.local
        self.guide_src = None
        return None

    def set(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.report(state)

    def dispatch(self, plan: dict) -> None:
        self.plan = plan
        turn_s = abs(plan.get("heading_deg", 0.0)) / TURN_DEG_PER_S
        self.turn_dir = 1.0 if plan.get("heading_deg", 0.0) >= 0 else -1.0
        self.until = time.time() + turn_s
        self.set("turning")

    def on_command(self, m: dict) -> None:
        t = m.get("type")
        if t == "dispatch":
            self.dispatch(m)
        elif t == "follow":
            self.follow, self.follow_ts = m, time.time()
        elif t == "stop":
            self.follow = None
            if self.state in ("approaching", "searching", "driving", "turning"):
                self.hw.stop()
                self.set("stopped")

    def tick(self) -> None:
        now = time.time()
        guide = self._guide(now)
        fresh = guide is not None
        if self.state == "turning":
            if now < self.until:
                self.hw.drive(0.0, 0.5 * self.turn_dir)
            else:
                self.until = now + self.plan.get("distance_m", 1.5) / DRIVE_M_PER_S
                self.set("driving")
        elif self.state == "driving":
            if fresh:
                self.set("approaching")
            elif now < self.until:
                self.hw.drive(DRIVE_SPEED, 0.0)
            else:
                self.set("searching")
        elif self.state == "searching":
            if fresh:
                self.set("approaching")
            else:
                self.hw.drive(0.0, SEARCH_TURN)
        elif self.state == "approaching":
            if not fresh:
                self.hw.stop()  # hold on visual or link loss
                last = max(self.follow_ts, self.local_ts)
                self.set("searching" if now - last > 3.0 else "approaching")
                return
            ex, _ = guide["err"]
            size = guide.get("size", 0.0)
            if size >= ARRIVE_BOX_H:
                self.hw.stop()
                self.set("arrived")
                return
            turn = max(-0.4, min(0.4, 1.2 * ex))
            forward = 0.0 if abs(ex) > 0.25 else DRIVE_SPEED * 0.6
            self.hw.drive(forward, turn)
        elif self.state == "arrived" and fresh and guide.get("size", 1.0) < ARRIVE_BOX_H * 0.7:
            self.set("approaching")  # target drifted away again


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


async def run(url: str, cam_index: int, hw, node: str = "B", fps: float = 10.0,
              onboard: str = "person"):
    import cv2

    global ARRIVE_BOX_H
    ARRIVE_BOX_H = ARRIVE_BY_TARGET.get(onboard, ARRIVE_BOX_H)
    person = PersonHOG() if onboard == "person" else None
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    follower = Follower(hw)
    outbox: list = []
    rover = Rover(hw, lambda st: outbox.append({"type": "rover_state", "state": st,
                                                "onboard": rover.onboard()}))
    rover.onboard_label = onboard
    if onboard == "green" and ballcolor is None:
        print("onboard classifier unavailable (ballcolor.py not found): ground guidance only")
    n = [0]

    def grab():
        ok, frame = cap.read()
        n[0] += 1
        if ok and person is not None and n[0] % 2 == 0:  # HOG every other frame (~5 Hz)
            rover.on_local(person.best(frame))
        elif ok and onboard == "green" and ballcolor is not None:
            res = ballcolor.find_balls(frame)
            rover.on_local(res["target"], len(res["decoys"]))
        return ok, frame
    session = "turbopi-" + uuid.uuid4().hex[:6]
    seq = 0
    ws_url = url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://") + f"/ws/scout?node={node}"
    while True:
        try:
            async with websockets.connect(ws_url, max_size=None, ping_interval=5) as ws:
                print("connected", ws_url)

                async def receiver():
                    async for msg in ws:
                        m = json.loads(msg)
                        if "pong" in m:
                            await ws.send(json.dumps({"sync": m["pong"], "srv": m["srv"], "recv": time.time() * 1000}))
                        elif m.get("type") in ("follow", "hold", "stop", "dispatch"):
                            rover.on_command(m)
                            if rover.state in ("idle", "arrived", "stopped") and m["type"] != "dispatch":
                                follower.command(m)  # pan-tilt keeps the target centred when parked

                async def pinger():
                    while True:
                        await ws.send(json.dumps({"ping": time.time() * 1000}))
                        await asyncio.sleep(1.0)

                async def control():
                    while True:
                        rover.tick()
                        while outbox:
                            await ws.send(json.dumps(outbox.pop(0)))
                        await asyncio.sleep(0.1)

                tasks = [asyncio.create_task(receiver()), asyncio.create_task(pinger()),
                         asyncio.create_task(control())]
                period = 1.0 / fps
                try:
                    while True:
                        t0 = time.time()
                        ok, frame = await asyncio.to_thread(grab)
                        if not ok:
                            await asyncio.sleep(0.2)
                            continue
                        ts = time.time() * 1000
                        h, w = frame.shape[:2]
                        ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        seq += 1
                        hdr = json.dumps({"node_id": node, "session_id": session, "seq": seq,
                                          "capture_ts_ms": ts, "width": w, "height": h}).encode()
                        await ws.send(struct.pack("<I", len(hdr)) + hdr + jpg.tobytes())
                        await asyncio.sleep(max(0.0, period - (time.time() - t0)))
                finally:
                    for t in tasks:
                        t.cancel()
        except Exception as e:  # noqa: BLE001
            hw.stop()  # never keep driving without the ground link
            print("link error:", e, "- retrying in 1 s")
            await asyncio.sleep(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--node", default="B")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--hw", default="none", choices=["none", "hiwonder"])
    ap.add_argument("--onboard", default="green", choices=["person", "green", "none"])
    a = ap.parse_args()
    hw = HiwonderHardware() if a.hw == "hiwonder" else NoHardware()
    asyncio.run(run(a.url, a.camera, hw, a.node, onboard=a.onboard))


if __name__ == "__main__":
    main()
