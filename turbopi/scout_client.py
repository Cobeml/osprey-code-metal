#!/usr/bin/env python3
"""Rover scout client for the Hiwonder TurboPi: camera -> Osprey (same binary WS protocol as the
phone page); dispatch/follow/stop commands -> mecanum chassis. The rover has no pan-tilt: it
steers its whole body toward the target.

Usage on the TurboPi:
  python3 scout_client.py <url> [--node B] [--camera 0] [--hw none|hiwonder] [--onboard green|person|none]
  python3 scout_client.py --selftest --hw hiwonder      # short guarded moves to check directions
  <url> is ws://169.254.50.2:8000 on the wired switch, or the https://<tunnel> URL.

Dispatch flow (rover starts beside the deck camera, facing along its optical axis):
  {"type":"dispatch","heading_deg","distance_m"} -> "turning" to the heading -> "driving": drive
  forward until the target is recognised, for at most distance_m + EXTRA_SEARCH_M (timed, no wheel
  encoders) -> "searching": spin slowly in place until it is recognised -> "approaching": lock on
  to that target, turn toward it and drive until its box is big enough -> "arrived": keeps
  following the ball if it moves (turns in place to keep it centred, drives after it when it moves
  away). Losing the target holds position; after LOST_TO_SEARCH_S without it the rover searches.
  Every state change is reported as {"type":"rover_state","state":...,"onboard":{...}}.

Recognition: the rover's own Pi runs --onboard "green" (the ground's green/red ball classifier,
src/osprey/perception/ballcolor.py, copied next to this file or run from the repo; red balls are
decoys and never steer it), "person" (OpenCV HOG, CPU only) or "none". Once it sees the target it
LOCKS on: later frames only accept the box nearest the locked one (within LOCK_GATE), so a second
green blob cannot steal it. The onboard lock steers first; the ground's follow error (Hailo on the
ground Pi) steers when the rover has no fresh onboard sighting. Stop always wins, and the rover
stops whenever the link to the ground drops.

Protocol: binary uint32 LE header_len | header JSON | JPEG, header {node_id, session_id, seq,
capture_ts_ms, width, height}; clock pings {"ping": ms} -> {"pong","srv"} -> {"sync","srv","recv"}.
Commands from the ground: {"type":"dispatch",...}, {"type":"follow","err":[ex,ey],"size"}
(normalized box-center error and box height), {"type":"hold"}, {"type":"stop"}.
"""
import argparse
import asyncio
import atexit
import json
import os
import struct
import sys
import time
import uuid
from pathlib import Path


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

STALE_S = 1.0             # a sighting or follow error older than this does not steer

# timed dead reckoning: calibrate on the floor at the venue with --selftest and a tape measure
DRIVE_SPEED = 0.5         # fraction of max
DRIVE_M_PER_S = 0.25      # measured ground speed at DRIVE_SPEED
TURN_DEG_PER_S = 90.0     # measured spin rate at turn=0.5
SEARCH_TURN = 0.25
EXTRA_SEARCH_M = 1.0      # keep driving this far past the dispatch distance before spinning
LOST_TO_SEARCH_S = 3.0    # lost target this long while approaching -> search again
LOCK_GATE = 0.25          # max box-centre jump (fraction of frame) that still counts as the lock
APPROACH_TURN_GAIN = 1.2
APPROACH_MAX_TURN = 0.4
APPROACH_ALIGN_ERR = 0.25  # turn in place until the target is within this of centre
APPROACH_SPEED = 0.6       # fraction of DRIVE_SPEED while approaching
HOLD_DEADBAND = 0.08      # while arrived, turn to re-centre when the ball is off-centre by more
REAPPROACH_FRAC = 0.7     # while arrived, drive after the ball when its box shrinks below this
ARRIVE_BOX_H = 0.85       # target box height (fraction of frame) that counts as "arrived"
ARRIVE_BY_TARGET = {"person": 0.85, "green": 0.45, "none": 0.85}


class NoHardware:
    """Video-only scout: prints what it would do (driving not demonstrated)."""

    def drive(self, forward: float, turn: float) -> None:
        """forward in [-1, 1] (fraction of max speed), turn in [-1, 1] (+ = clockwise)."""
        print(f"drive forward={forward:+.2f} turn={turn:+.2f}")

    def stop(self) -> None:
        print("stop")


# Hiwonder SDK mapping. MecanumChassis.set_velocity(speed, direction_deg, yaw_rate):
# direction 90 = forward, 270 = backward; (0, 0, 0) stops; positive yaw = clockwise per the
# Hiwonder mecanum chassis wiki. Speed and yaw scales differ between Hiwonder docs, so these are
# conservative and must be checked with --selftest on the real rover.
SDK_PATHS = ("/home/pi/TurboPi", "/home/pi/TurboPi/HiwonderSDK/..", "/home/pi")
SDK_MAX_SPEED = 100.0     # set_velocity speed at forward = 1.0
SDK_MAX_YAW = 1.0         # set_velocity yaw at turn = 1.0 (docs show a -2..2 range)
SDK_YAW_SIGN = 1.0        # flip to -1 if --selftest shows the "clockwise" spin going anticlockwise
SDK_FORWARD_DEG = 90.0
SDK_BACKWARD_DEG = 270.0


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class HiwonderHardware(NoHardware):
    """Mecanum chassis through HiwonderSDK.mecanum (TurboPi image). No pan-tilt on this rover."""

    def __init__(self, chassis=None):
        self.chassis = chassis if chassis is not None else self._open_chassis()
        self.last = (0.0, 0.0, 0.0)
        atexit.register(self.stop)  # never leave the wheels turning when the client exits

    @staticmethod
    def _open_chassis():
        extra = os.environ.get("TURBOPI_SDK")
        for p in ((extra,) if extra else ()) + SDK_PATHS:
            p = os.path.normpath(p)
            if os.path.isdir(p) and p not in sys.path:
                sys.path.append(p)
        try:
            import HiwonderSDK.mecanum as mecanum
        except ImportError as e:
            raise SystemExit(
                "HiwonderSDK not found. Find the folder containing HiwonderSDK/ on the TurboPi "
                "(e.g. `find / -name mecanum.py -path '*Hiwonder*' 2>/dev/null`) and run with "
                f"TURBOPI_SDK=<that folder>. ({e})")
        return mecanum.MecanumChassis()

    @staticmethod
    def to_sdk(forward: float, turn: float) -> tuple:
        forward, turn = _clamp(forward), _clamp(turn)
        speed = abs(forward) * SDK_MAX_SPEED
        direction = SDK_FORWARD_DEG if forward >= 0 else SDK_BACKWARD_DEG
        yaw = SDK_YAW_SIGN * turn * SDK_MAX_YAW
        return (round(speed, 1), direction, round(yaw, 3))

    def drive(self, forward: float, turn: float) -> None:
        cmd = self.to_sdk(forward, turn)
        self.chassis.set_velocity(*cmd)
        self.last = cmd

    def stop(self) -> None:
        self.chassis.set_velocity(0, 0, 0)
        self.last = (0.0, 0.0, 0.0)


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


def _centre(bbox) -> tuple:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


class Rover:
    """Dispatch state machine. tick() runs ~10 Hz."""

    def __init__(self, hw, report):
        self.hw, self.report = hw, report
        self.state = "idle"
        self.until = 0.0
        self.plan = None
        self.follow = None  # last ground follow message
        self.follow_ts = 0.0
        self.local = None   # locked onboard sighting, same shape as a follow message
        self.local_ts = 0.0
        self.lock_centre = None
        self.decoys = 0     # red balls in the last onboard frame
        self.guide_src = None

    # ----------------------------------------------------------- recognition
    def locked(self, now: float = None) -> bool:
        now = time.time() if now is None else now
        return self.lock_centre is not None and now - self.local_ts <= STALE_S

    def on_local(self, targets, decoys: int = 0) -> None:
        """Onboard result for one frame: None, one {"bbox","confidence"} box, or a list of them.
        Unlocked: take the most confident box and lock on. Locked: only the box nearest the lock
        (within LOCK_GATE) counts, so another green blob cannot steal the target."""
        self.decoys = decoys
        if targets is None:
            return
        cands = [targets] if isinstance(targets, dict) else list(targets)
        if not cands:
            return
        now = time.time()
        if self.locked(now):
            lx, ly = self.lock_centre

            def dist(d):
                cx, cy = _centre(d["bbox"])
                return ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5

            best = min(cands, key=dist)
            if dist(best) > LOCK_GATE:
                return  # not our target: the lock goes stale unless it comes back
        else:
            best = max(cands, key=lambda d: d["confidence"])
        cx, cy = _centre(best["bbox"])
        x1, y1, x2, y2 = best["bbox"]
        self.lock_centre = (cx, cy)
        self.local = {"err": [cx - 0.5, cy - 0.5], "size": y2 - y1, "confidence": best["confidence"]}
        self.local_ts = now

    def onboard(self) -> dict:
        """What the rover's own camera says, reported with every state change."""
        fresh = self.local is not None and time.time() - self.local_ts <= STALE_S
        label = getattr(self, "onboard_label", "green")
        return {"label": label if fresh else None, "color": "green" if fresh and label == "green" else None,
                "confidence": round(self.local["confidence"], 2) if fresh else None,
                "decoys": self.decoys, "guide": self.guide_src, "locked": fresh,
                "classifier": ballcolor is not None}

    def _guide(self, now: float):
        """The rover's own lock first, then the ground's follow error, else None."""
        if self.local is not None and now - self.local_ts <= STALE_S:
            self.guide_src = "onboard"
            return self.local
        if self.follow is not None and now - self.follow_ts <= STALE_S:
            self.guide_src = "ground"
            return self.follow
        self.guide_src = None
        return None

    # ----------------------------------------------------------- commands
    def set(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.report(state)

    def dispatch(self, plan: dict) -> None:
        self.plan = plan
        self.lock_centre = None  # a new dispatch starts a fresh search
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

    # ----------------------------------------------------------- control
    def tick(self) -> None:
        now = time.time()
        guide = self._guide(now)
        fresh = guide is not None
        if self.state == "turning":
            if now < self.until:
                self.hw.drive(0.0, 0.5 * self.turn_dir)
            else:
                dist = self.plan.get("distance_m", 1.5) + EXTRA_SEARCH_M
                self.until = now + dist / DRIVE_M_PER_S
                self.set("driving")
        elif self.state == "driving":  # drive forward until the target is recognised
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
                if now - last > LOST_TO_SEARCH_S:
                    self.lock_centre = None
                    self.set("searching")
                return
            ex, _ = guide["err"]
            size = guide.get("size", 0.0)
            if size >= ARRIVE_BOX_H:
                self.hw.stop()
                self.set("arrived")
                return
            turn = _clamp(APPROACH_TURN_GAIN * ex, -APPROACH_MAX_TURN, APPROACH_MAX_TURN)
            forward = 0.0 if abs(ex) > APPROACH_ALIGN_ERR else DRIVE_SPEED * APPROACH_SPEED
            self.hw.drive(forward, turn)
        elif self.state == "arrived":  # keep following the ball if it moves
            if not fresh:
                self.hw.stop()
                last = max(self.follow_ts, self.local_ts)
                if now - last > LOST_TO_SEARCH_S:
                    self.lock_centre = None
                    self.set("searching")  # ball left the frame: look for it again
                return
            ex, _ = guide["err"]
            if guide.get("size", 1.0) < ARRIVE_BOX_H * REAPPROACH_FRAC:
                self.set("approaching")  # ball moved away: drive after it
            elif abs(ex) > HOLD_DEADBAND:
                self.hw.drive(0.0, _clamp(APPROACH_TURN_GAIN * ex, -APPROACH_MAX_TURN, APPROACH_MAX_TURN))
            else:
                self.hw.stop()  # centred and close: hold


SELFTEST_S = 1.0


def selftest(hw) -> None:
    """Short guarded moves to confirm directions and measure speed. Lift or clear the rover."""
    moves = [("forward", DRIVE_SPEED, 0.0), ("backward", -DRIVE_SPEED, 0.0),
             ("spin clockwise (seen from above)", 0.0, 0.5), ("spin anticlockwise", 0.0, -0.5)]
    try:
        for name, f, t in moves:
            if input(f"{name} for {SELFTEST_S:.0f} s? [Enter = go, s = skip, q = quit] ").strip().lower() == "q":
                break
            hw.drive(f, t)
            time.sleep(SELFTEST_S)
            hw.stop()
        print("Measure distance at DRIVE_SPEED and degrees at turn=0.5 over a longer run, then set\n"
              "DRIVE_M_PER_S / TURN_DEG_PER_S; flip SDK_YAW_SIGN if the clockwise spin went the other way.")
    finally:
        hw.stop()


async def run(url: str, cam_index: int, hw, node: str = "B", fps: float = 10.0,
              onboard: str = "green"):
    import cv2
    import websockets

    global ARRIVE_BOX_H
    ARRIVE_BOX_H = ARRIVE_BY_TARGET.get(onboard, ARRIVE_BOX_H)
    person = PersonHOG() if onboard == "person" else None
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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
            rover.on_local(res.get("greens", res["target"]), len(res["decoys"]))
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
    ap.add_argument("url", nargs="?")
    ap.add_argument("--node", default="B")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--hw", default="none", choices=["none", "hiwonder"])
    ap.add_argument("--onboard", default="green", choices=["person", "green", "none"])
    ap.add_argument("--selftest", action="store_true", help="guarded chassis moves, no network")
    a = ap.parse_args()
    hw = HiwonderHardware() if a.hw == "hiwonder" else NoHardware()
    if a.selftest:
        selftest(hw)
        return
    if not a.url:
        ap.error("url is required unless --selftest")
    try:
        asyncio.run(run(a.url, a.camera, hw, a.node, onboard=a.onboard))
    finally:
        hw.stop()


if __name__ == "__main__":
    main()
