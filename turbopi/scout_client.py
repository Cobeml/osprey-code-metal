#!/usr/bin/env python3
"""Rover scout client for the Hiwonder TurboPi: camera -> Osprey (same binary WS protocol as the
phone page); dispatch/follow/stop commands -> mecanum chassis and an optional pan servo.

Pan camera (--pan-call ...): the camera leads, the body follows. While locked, the pan keeps the
target centred in the image and the body steers toward pan angle + image error; searching sweeps
the camera with the body still and spins the body only after a full sweep; while arrived, small
moves are followed by the pan alone. Without --pan-call the body does all the steering.

Usage on the TurboPi:
  python3 scout_client.py <url> [--node B] [--camera 0] [--hw none|hiwonder] [--onboard green|person|none]
                          [--pan-call MODULE:FUNC --pan-id N --pan-center US --pan-sign 1|-1]
  python3 scout_client.py --probe                       # list the SDK's servo/chassis calls (read-only)
  python3 scout_client.py --selftest --hw hiwonder [--pan-call ...]   # short guarded moves
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
import signal
import struct
import sys
import time
import uuid


async def _in_thread(fn):
    """asyncio.to_thread needs Python 3.9; older Hiwonder images may ship 3.7/3.8."""
    if hasattr(asyncio, "to_thread"):
        return await asyncio.to_thread(fn)
    return await asyncio.get_event_loop().run_in_executor(None, fn)


def _exit_on_sigterm() -> None:
    """kill / deploy_rover.sh stop sends SIGTERM, which skips atexit and finally blocks by
    default; turn it into a normal exit so the wheels are always stopped."""
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
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

# pan camera (camera leads, body follows). Pan angle: 0 = straight ahead, + = right (clockwise).
CAM_HFOV_DEG = 120.0      # horizontal field of view; retail listings say 120-130 deg wide angle
PAN_LIMIT_DEG = 80.0
PAN_GAIN = 0.6            # fraction of the image error (in deg) corrected per tick
PAN_MAX_STEP_DEG = 6.0    # per tick (~10 Hz)
PAN_DEADBAND_DEG = 2.0
PAN_SWEEP_DEG = 70.0      # search sweep half-width
PAN_SWEEP_DEG_PER_S = 60.0
SEARCH_SPIN_S = 1.5       # after a full sweep with nothing seen, spin the body this long
ARRIVED_BODY_DEG = 20.0   # while arrived, the body re-turns once the pan is past this


class NoHardware:
    """Video-only scout: prints what it would do (driving not demonstrated)."""

    has_pan = False

    def set_pan(self, deg: float) -> None:
        pass

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


def _add_sdk_paths() -> None:
    extra = os.environ.get("TURBOPI_SDK")
    for p in ((extra,) if extra else ()) + SDK_PATHS:
        p = os.path.normpath(p)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.append(p)


class PulseServo:
    """Pan servo driven by a Hiwonder-style call fn(servo_id, pulse_us, move_ms).

    UNVERIFIED: the TurboPi's servo call is not documented publicly. Run --probe on the rover to
    list the SDK's servo functions, then pass e.g. --pan-call HiwonderSDK.Board:setPWMServoPulse
    --pan-id <id>. Typical hobby servos: 500-2500 us over ~180 deg (≈11.1 us/deg), 1500 = centre;
    check centre and direction with --selftest."""

    def __init__(self, fn, servo_id: int, center_us: float = 1500.0, us_per_deg: float = 11.1,
                 sign: float = 1.0, move_ms: int = 60, limit_deg: float = PAN_LIMIT_DEG):
        self.fn, self.servo_id = fn, servo_id
        self.center_us, self.us_per_deg, self.sign = center_us, us_per_deg, sign
        self.move_ms, self.limit_deg = move_ms, limit_deg

    def pulse(self, deg: float) -> int:
        deg = _clamp(deg, -self.limit_deg, self.limit_deg)
        return int(round(self.center_us + self.sign * deg * self.us_per_deg))

    def set(self, deg: float) -> None:
        self.fn(self.servo_id, self.pulse(deg), self.move_ms)

    @staticmethod
    def resolve(spec: str):
        """'package.module:function' -> callable, importing from the TurboPi SDK path."""
        import importlib

        _add_sdk_paths()
        mod, _, name = spec.partition(":")
        return getattr(importlib.import_module(mod), name)


class HiwonderHardware(NoHardware):
    """Mecanum chassis through HiwonderSDK.mecanum (TurboPi image), plus an optional pan servo."""

    def __init__(self, chassis=None, pan: "PulseServo" = None):
        self.chassis = chassis if chassis is not None else self._open_chassis()
        self.pan = pan
        self.last = (0.0, 0.0, 0.0)
        atexit.register(self.stop)  # never leave the wheels turning when the client exits

    @property
    def has_pan(self) -> bool:
        return self.pan is not None

    def set_pan(self, deg: float) -> None:
        if self.pan is not None:
            self.pan.set(deg)

    @staticmethod
    def _open_chassis():
        _add_sdk_paths()
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
        self.pan_deg = 0.0  # commanded pan angle (+ = right); stays 0 without a pan servo
        self.pan_applied_ts = 0.0  # sighting time last used for a pan correction
        self.sweep_dir = 1.0
        self.half_sweeps = 0
        self.spin_until = 0.0
        self.last_tick = None

    # ----------------------------------------------------------- pan camera
    def _set_pan(self, deg: float) -> None:
        self.pan_deg = _clamp(deg, -PAN_LIMIT_DEG, PAN_LIMIT_DEG)
        self.hw.set_pan(self.pan_deg)

    def _track_pan(self, ex: float, sighting_ts: float) -> None:
        """Camera leads: re-centre the target in the image, once per new sighting."""
        if not self.hw.has_pan or sighting_ts <= self.pan_applied_ts:
            return
        self.pan_applied_ts = sighting_ts
        err_deg = ex * CAM_HFOV_DEG
        if abs(err_deg) > PAN_DEADBAND_DEG:
            step = _clamp(PAN_GAIN * err_deg, -PAN_MAX_STEP_DEG, PAN_MAX_STEP_DEG)
            self._set_pan(self.pan_deg + step)

    def _bearing(self, ex: float) -> float:
        """Target direction relative to the body, as a fraction of the camera's field of view
        (equals the image error when the camera faces straight ahead)."""
        return (self.pan_deg + ex * CAM_HFOV_DEG) / CAM_HFOV_DEG

    def _search(self, now: float, dt: float) -> None:
        """With a pan camera: sweep it with the body still, spin the body after each full sweep.
        Without one: spin the body."""
        if not self.hw.has_pan or now < self.spin_until:
            self.hw.drive(0.0, SEARCH_TURN)
            return
        self.hw.stop()
        nxt = self.pan_deg + self.sweep_dir * PAN_SWEEP_DEG_PER_S * dt
        if abs(nxt) >= PAN_SWEEP_DEG:
            nxt = PAN_SWEEP_DEG * self.sweep_dir
            self.sweep_dir = -self.sweep_dir
            self.half_sweeps += 1
            if self.half_sweeps >= 2:  # looked both ways: turn the body to a fresh sector
                self.half_sweeps = 0
                nxt = 0.0
                self.spin_until = now + SEARCH_SPIN_S
        self._set_pan(nxt)

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
                "pan_deg": round(self.pan_deg, 1) if self.hw.has_pan else None,
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
        self.half_sweeps, self.spin_until = 0, 0.0
        self._set_pan(0.0)
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
        dt = 0.1 if self.last_tick is None else _clamp(now - self.last_tick, 0.0, 0.2)
        self.last_tick = now
        guide = self._guide(now)
        fresh = guide is not None
        if fresh and self.state in ("driving", "searching", "approaching", "arrived"):
            ts = self.local_ts if self.guide_src == "onboard" else self.follow_ts
            self._track_pan(guide["err"][0], ts)
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
                self._search(now, dt)
        elif self.state == "approaching":
            if not fresh:
                self.hw.stop()  # hold on visual or link loss
                last = max(self.follow_ts, self.local_ts)
                if now - last > LOST_TO_SEARCH_S:
                    self.lock_centre = None
                    self.set("searching")
                return
            b = self._bearing(guide["err"][0])
            size = guide.get("size", 0.0)
            if size >= ARRIVE_BOX_H:
                self.hw.stop()
                self.set("arrived")
                return
            turn = _clamp(APPROACH_TURN_GAIN * b, -APPROACH_MAX_TURN, APPROACH_MAX_TURN)
            forward = 0.0 if abs(b) > APPROACH_ALIGN_ERR else DRIVE_SPEED * APPROACH_SPEED
            self.hw.drive(forward, turn)
        elif self.state == "arrived":  # keep following the ball if it moves
            if not fresh:
                self.hw.stop()
                last = max(self.follow_ts, self.local_ts)
                if now - last > LOST_TO_SEARCH_S:
                    self.lock_centre = None
                    self.set("searching")  # ball left the frame: look for it again
                return
            b = self._bearing(guide["err"][0])
            # with a pan camera small moves are followed by the pan alone; the body re-turns
            # only once the target is well off the body's axis
            hold = ARRIVED_BODY_DEG / CAM_HFOV_DEG if self.hw.has_pan else HOLD_DEADBAND
            if guide.get("size", 1.0) < ARRIVE_BOX_H * REAPPROACH_FRAC:
                self.set("approaching")  # ball moved away: drive after it
            elif abs(b) > hold:
                self.hw.drive(0.0, _clamp(APPROACH_TURN_GAIN * b, -APPROACH_MAX_TURN, APPROACH_MAX_TURN))
            else:
                self.hw.stop()  # close and within the hold band: hold


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
        else:
            if hw.has_pan and input("pan sweep: centre, 30 deg right, 30 deg left, centre? "
                                    "[Enter = go, s = skip] ").strip().lower() != "s":
                for deg in (0.0, 30.0, -30.0, 0.0):
                    print(f"pan {deg:+.0f} deg")
                    hw.set_pan(deg)
                    time.sleep(SELFTEST_S)
                print("If centre is off, adjust --pan-center; if +30 went left, pass --pan-sign -1.")
        print("Measure distance at DRIVE_SPEED and degrees at turn=0.5 over a longer run, then set\n"
              "DRIVE_M_PER_S / TURN_DEG_PER_S; flip SDK_YAW_SIGN if the clockwise spin went the other way.")
    finally:
        hw.stop()


def probe() -> None:
    """Read-only: where the Hiwonder SDK is and which servo/PWM/chassis functions it offers.
    Paste the output back so the pan call can be filled in. Moves nothing."""
    import importlib
    import inspect
    import pkgutil

    _add_sdk_paths()
    print("python", sys.version.split()[0], "| sys.path additions:",
          [p for p in sys.path if "TurboPi" in p or p == "/home/pi"])
    try:
        pkg = importlib.import_module("HiwonderSDK")
    except ImportError as e:
        print("HiwonderSDK not importable:", e)
        print("try: find / -name '*.py' -path '*Hiwonder*' 2>/dev/null | head -50")
        return
    print("HiwonderSDK at", getattr(pkg, "__path__", "?"))
    keys = ("servo", "pwm", "pulse", "velocity", "motor", "pan", "tilt")
    for info in pkgutil.iter_modules(pkg.__path__):
        name = f"HiwonderSDK.{info.name}"
        try:
            mod = importlib.import_module(name)  # import only; no function is called
        except Exception as e:  # noqa: BLE001 - some SDK modules need hardware at import
            print(f"  {name}: import failed ({type(e).__name__}: {e})")
            continue
        for attr, obj in inspect.getmembers(mod):
            if any(k in attr.lower() for k in keys) and callable(obj):
                try:
                    sig = str(inspect.signature(obj))
                except (TypeError, ValueError):
                    sig = "(?)"
                print(f"  {name}:{attr}{sig}")
            elif inspect.isclass(obj) and obj.__module__ == mod.__name__:
                for m, fn in inspect.getmembers(obj, callable):
                    if any(k in m.lower() for k in keys):
                        try:
                            sig = str(inspect.signature(fn))
                        except (TypeError, ValueError):
                            sig = "(?)"
                        print(f"  {name}:{attr}.{m}{sig}")
    print("video devices:", sorted(p for p in os.listdir("/dev") if p.startswith("video"))
          if os.path.isdir("/dev") else "?")


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
                        ok, frame = await _in_thread(grab)
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
    ap.add_argument("--selftest", action="store_true", help="guarded chassis/pan moves, no network")
    ap.add_argument("--probe", action="store_true", help="list the Hiwonder SDK's servo/chassis calls; moves nothing")
    ap.add_argument("--pan-call", default="", help="pan servo call fn(id, pulse_us, ms), e.g. "
                    "HiwonderSDK.Board:setPWMServoPulse (find it with --probe); empty = no pan")
    ap.add_argument("--pan-id", type=int, default=2)
    ap.add_argument("--pan-center", type=float, default=1500.0, help="pulse (us) that points straight ahead")
    ap.add_argument("--pan-us-per-deg", type=float, default=11.1)
    # at the venue the pan turned left when commanded right (tilt fine): default -1; pass
    # --pan-sign 1 if a re-mount fixes it
    ap.add_argument("--pan-sign", type=float, default=-1.0, choices=[1.0, -1.0])
    a = ap.parse_args()
    _exit_on_sigterm()
    if a.probe:
        probe()
        return
    pan = None
    if a.pan_call:
        pan = PulseServo(PulseServo.resolve(a.pan_call), a.pan_id, a.pan_center,
                         a.pan_us_per_deg, a.pan_sign)
    if pan is not None and a.hw != "hiwonder":
        ap.error("--pan-call needs --hw hiwonder")
    hw = HiwonderHardware(pan=pan) if a.hw == "hiwonder" else NoHardware()
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
