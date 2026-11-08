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
import threading
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
TURN_DEG_PER_S = 280.0    # venue TurboPi: ~170 deg/s at turn=0.3 (camera-measured, rough; it coasts)
SEARCH_TURN = 0.2
EXTRA_SEARCH_M = 1.0      # keep driving this far past the dispatch distance before spinning
LOST_TO_SEARCH_S = 3.0    # lost target this long while approaching -> search again
LOCK_GATE = 0.4           # max box-centre jump (fraction of frame) that still counts as the lock
                          # (0.25 dropped good locks while the rover turned; one green ball in the demo)
APPROACH_TURN_GAIN = 0.5  # turns ~3x faster than first assumed: was 1.2 and overshot
APPROACH_MAX_TURN = 0.2
APPROACH_MIN_TURN = 0.12  # below this the motors don't move the body (trace: 0.145 turns it)
APPROACH_TURN_DEADBAND = 0.05
TURN_FRESH_S = 0.25       # only turn on a sighting this recent; blurred frames pause the turn
APPROACH_ALIGN_ERR = 0.15  # turn in place until the target is within this of centre
APPROACH_SPEED = 0.6       # fraction of DRIVE_SPEED while approaching
HOLD_DEADBAND = 0.08      # while arrived, turn to re-centre when the ball is off-centre by more
REAPPROACH_FRAC = 0.7     # while arrived, drive after the ball when its box shrinks below this
ARRIVE_BOX_H = 0.85       # target box height (fraction of frame) that counts as "arrived"
ARRIVE_BY_TARGET = {"person": 0.85, "green": 0.35, "none": 0.85}  # green: with a level camera the
# ball slipped under the view at ~0.24 of the frame height; the tilt now follows it down
# tilt camera (venue TurboPi: servo 2, higher pulse = down). Follows the ball down as the rover
# closes in, and looks down for a ball that dropped out of the bottom of the frame.
TILT_DOWN_LIMIT_US = 1500.0   # looking at the floor just in front of the chassis
TILT_STEP_US = 50.0           # ~4.5 deg per step
TILT_US_PER_DEG = 11.1
TILT_LOW_Y = 0.7              # box centre below this (fraction of height): tilt down a step
TILT_HIGH_Y = 0.35            # box centre above this: tilt back up a step (not above the start)
TILT_LOST_Y = 0.6             # lost while this low: it went out the bottom, look down for it
TILT_LOST_STEP_S = 0.15

# pan camera (camera leads, body follows). Pan angle: 0 = straight ahead, + = right (clockwise).
CAM_HFOV_DEG = 60.0       # measured on the venue TurboPi (upright mount, 03:45): 40 deg of pan moved the ball
                          # ~0.68 of the width -> ~60 deg. Retail listings say 120.
PAN_LIMIT_DEG = 80.0
PAN_GAIN = 0.5            # fraction of the image error (in deg) corrected per tick
PAN_MAX_STEP_DEG = 4.0    # per tick (~10 Hz)
PAN_DEADBAND_DEG = 2.0
PAN_SWEEP_DEG = 70.0      # search sweep half-width
PAN_SWEEP_DEG_PER_S = 60.0
SEARCH_SPIN_S = 0.35      # after a full sweep with nothing seen, spin the body this long (~50 deg)
ARRIVED_BODY_DEG = 20.0   # (unused since the body alone steers at the ball)
ARRIVED_HOLD_ERR = 0.1    # at the ball: hold still while it is within this of centre


class NoHardware:
    """Video-only scout: prints what it would do (driving not demonstrated)."""

    has_pan = False
    tilt_base_us = None

    def set_pan(self, deg: float) -> None:
        pass

    def set_tilt(self, us: float) -> None:
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


TRACE = os.environ.get("ROVER_TRACE") == "1"   # one log line per tick + lock decisions


def _trace(msg: str) -> None:
    if TRACE:
        print(f"{time.time():.2f} {msg}", flush=True)


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

    def __init__(self, chassis=None, pan: "PulseServo" = None, tilt: tuple = None):
        """tilt: (fn, servo_id, start_us) for the camera tilt servo, or None."""
        self.chassis = chassis if chassis is not None else self._open_chassis()
        self.pan = pan
        self.tilt = tilt
        self.tilt_base_us = tilt[2] if tilt else None
        self.last = (0.0, 0.0, 0.0)
        atexit.register(self.stop)  # never leave the wheels turning when the client exits

    def set_tilt(self, us: float) -> None:
        if self.tilt is not None:
            fn, sid, _ = self.tilt
            fn(sid, int(us), 80)

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
        self.tilt_us = getattr(hw, "tilt_base_us", None)   # None: no tilt servo
        self.tilt_applied_ts = 0.0
        self.tilt_step_ts = 0.0
        self.last_cy = 0.5
        self.pan_applied_ts = 0.0  # sighting time last used for a pan correction
        self.sweep_dir = 1.0
        self.half_sweeps = 0
        self.spin_until = 0.0
        self.last_tick = None

    # ----------------------------------------------------------- pan camera
    def _set_pan(self, deg: float) -> None:
        new = _clamp(deg, -PAN_LIMIT_DEG, PAN_LIMIT_DEG)
        if self.lock_centre is not None and new != self.pan_deg:
            # panning right moves the ball left in the image: move the lock window with it
            lx, ly = self.lock_centre
            self.lock_centre = (lx - (new - self.pan_deg) / CAM_HFOV_DEG, ly)
        self.pan_deg = new
        self.hw.set_pan(self.pan_deg)

    # ----------------------------------------------------------- tilt camera
    def _set_tilt(self, us: float) -> None:
        if self.tilt_us is None:
            return
        base = self.hw.tilt_base_us
        new = _clamp(us, min(base, TILT_DOWN_LIMIT_US), TILT_DOWN_LIMIT_US)
        if new == self.tilt_us:
            return
        if self.lock_centre is not None:
            # tilting down moves the ball up in the image: move the lock window with it
            lx, ly = self.lock_centre
            self.lock_centre = (lx, ly - (new - self.tilt_us) / TILT_US_PER_DEG / (CAM_HFOV_DEG * 0.75))
        self.tilt_us = new
        self.hw.set_tilt(new)

    def _track_tilt(self, cy: float, sighting_ts: float) -> None:
        """Keep the ball off the bottom edge as the rover closes in; once per new sighting."""
        self.last_cy = cy
        if self.tilt_us is None or sighting_ts <= self.tilt_applied_ts:
            return
        self.tilt_applied_ts = sighting_ts
        if cy > TILT_LOW_Y:
            self._set_tilt(self.tilt_us + TILT_STEP_US)
        elif cy < TILT_HIGH_Y and self.tilt_us > self.hw.tilt_base_us:
            self._set_tilt(self.tilt_us - TILT_STEP_US)

    def _look_down_if_lost_low(self, now: float) -> None:
        """Ball vanished while low in the frame: it went out the bottom, so tilt down for it."""
        if self.tilt_us is not None and self.last_cy > TILT_LOST_Y and \
                self.tilt_us < TILT_DOWN_LIMIT_US and now - self.tilt_step_ts >= TILT_LOST_STEP_S:
            self.tilt_step_ts = now
            self._set_tilt(self.tilt_us + TILT_STEP_US)

    def _track_pan(self, ex: float, sighting_ts: float) -> None:
        """Camera leads: re-centre the target in the image, once per new sighting."""
        if not self.hw.has_pan or sighting_ts <= self.pan_applied_ts:
            return
        self.pan_applied_ts = sighting_ts
        err_deg = ex * CAM_HFOV_DEG
        if abs(err_deg) > PAN_DEADBAND_DEG:
            step = _clamp(PAN_GAIN * err_deg, -PAN_MAX_STEP_DEG, PAN_MAX_STEP_DEG)
            self._set_pan(self.pan_deg + step)

    @staticmethod
    def _body_turn(b: float) -> float:
        """Bounded body turn for bearing b (fraction of FOV): zero inside the deadband, otherwise
        at least the turn that actually moves the chassis and at most APPROACH_MAX_TURN."""
        if abs(b) <= APPROACH_TURN_DEADBAND:
            return 0.0
        mag = _clamp(APPROACH_TURN_GAIN * abs(b), APPROACH_MIN_TURN, APPROACH_MAX_TURN)
        return mag if b > 0 else -mag

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
            _trace("det none")
            return
        cands = [targets] if isinstance(targets, dict) else list(targets)
        if not cands:
            _trace("det none")
            return
        now = time.time()
        if self.locked(now):
            lx, ly = self.lock_centre

            def dist(d):
                cx, cy = _centre(d["bbox"])
                return ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5

            best = min(cands, key=dist)
            if dist(best) > LOCK_GATE:
                _trace(f"det rejected: {len(cands)} green, nearest {dist(best):.2f} from lock "
                       f"({lx:.2f},{ly:.2f}) > gate {LOCK_GATE}")
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
            if state == "searching" and self.tilt_us is not None:
                self._set_tilt(self.hw.tilt_base_us)   # search at the start tilt, not at the floor
                self.last_cy = 0.5
            self.state = state
            self.report(state)

    def dispatch(self, plan: dict) -> None:
        self.plan = plan
        self.lock_centre = None  # a new dispatch starts a fresh search
        self.half_sweeps, self.spin_until = 0, 0.0
        self._set_pan(0.0)
        if self.tilt_us is not None:
            self._set_tilt(self.hw.tilt_base_us)   # start each run at the level-ish start tilt
            self.last_cy = 0.5
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
        self._tick()
        if TRACE:
            g = self.local if self.guide_src == "onboard" else self.follow if self.guide_src else None
            _trace(f"tick {self.state} src={self.guide_src} "
                   f"err={None if not g else round(g['err'][0], 2)} size={None if not g else round(g.get('size', 0), 2)} "
                   f"pan={self.pan_deg:.1f} cmd={getattr(self.hw, 'last', None)}")

    def _tick(self) -> None:
        now = time.time()
        dt = 0.1 if self.last_tick is None else _clamp(now - self.last_tick, 0.0, 0.2)
        self.last_tick = now
        guide = self._guide(now)
        fresh = guide is not None
        if fresh and self.state in ("approaching", "arrived"):
            ts = self.local_ts if self.guide_src == "onboard" else self.follow_ts
            self._track_tilt(guide["err"][1] + 0.5, ts)
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
                self._look_down_if_lost_low(now)
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
            if self.pan_deg != 0.0:
                # one steerer at a time: centre the camera (the lock window follows) and let the
                # body turn by the full bearing; pan + body together overshot and oscillated
                self._set_pan(0.0)
            ts = self.local_ts if self.guide_src == "onboard" else self.follow_ts
            fresh_turn = now - ts <= TURN_FRESH_S
            if abs(b) > APPROACH_ALIGN_ERR:   # well off-centre: turn in place (needs the minimum)
                self.hw.drive(0.0, self._body_turn(b) if fresh_turn else 0.0)
            else:                             # roughly centred: drive and steer gently (no minimum)
                steer = 0.0 if abs(b) <= APPROACH_TURN_DEADBAND or not fresh_turn else \
                    _clamp(APPROACH_TURN_GAIN * b, -APPROACH_MAX_TURN, APPROACH_MAX_TURN)
                self.hw.drive(DRIVE_SPEED * APPROACH_SPEED, steer)
        elif self.state == "arrived":  # keep following the ball if it moves
            if not fresh:
                self.hw.stop()
                self._look_down_if_lost_low(now)
                last = max(self.follow_ts, self.local_ts)
                if now - last > LOST_TO_SEARCH_S:
                    self.lock_centre = None
                    self.set("searching")  # ball left the frame: look for it again
                return
            b = self._bearing(guide["err"][0])
            if self.pan_deg != 0.0:
                self._set_pan(0.0)   # one steerer at the ball too: pan + body together oscillated
            hold = ARRIVED_HOLD_ERR
            if guide.get("size", 1.0) < ARRIVE_BOX_H * REAPPROACH_FRAC:
                self.set("approaching")  # ball moved away: drive after it
            elif abs(b) > hold:
                ts = self.local_ts if self.guide_src == "onboard" else self.follow_ts
                self.hw.drive(0.0, self._body_turn(b) if now - ts <= TURN_FRESH_S else 0.0)
            else:
                self.hw.stop()  # close and within the hold band: hold


SELFTEST_S = 1.0


def selftest(hw) -> None:
    """Short guarded moves to confirm directions and measure speed. Lift or clear the rover."""
    moves = [("forward", DRIVE_SPEED, 0.0), ("backward", -DRIVE_SPEED, 0.0),
             ("spin clockwise (seen from above)", 0.0, 0.5), ("spin anticlockwise", 0.0, -0.5)]
    try:
        for name, f, t in moves:
            ans = input(f"{name} for {SELFTEST_S:.0f} s? [Enter = go, s = skip, q = quit] ").strip().lower()
            if ans == "q":
                break
            if ans == "s":   # skip really skips: no wheel command at all
                continue
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


ROTATE_CODES = {90: "ROTATE_90_CLOCKWISE", 180: "ROTATE_180", 270: "ROTATE_90_COUNTERCLOCKWISE"}


async def run(url: str, cam_index: int, hw, node: str = "B", fps: float = 10.0,
              onboard: str = "green", rotate: int = 0):
    import cv2
    import websockets

    global ARRIVE_BOX_H, CAM_HFOV_DEG
    rot = getattr(cv2, ROTATE_CODES[rotate]) if rotate in ROTATE_CODES else None
    if rotate in (90, 270):  # portrait after rotation: across the image is the camera's vertical FOV
        CAM_HFOV_DEG = CAM_HFOV_DEG * 0.75
    ARRIVE_BOX_H = ARRIVE_BY_TARGET.get(onboard, ARRIVE_BOX_H)
    person = PersonHOG() if onboard == "person" else None
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    # the camera runs faster than we process: a reader thread keeps only the newest frame, so the
    # controller never steers on a queued, seconds-old image
    latest = {"f": None, "n": 0}

    def reader():
        while True:
            ok_, f_ = cap.read()
            if ok_:
                latest["f"], latest["n"] = f_, latest["n"] + 1
            else:
                time.sleep(0.02)
    threading.Thread(target=reader, daemon=True).start()
    used = [0]
    outbox: list = []
    rover = Rover(hw, lambda st: outbox.append({"type": "rover_state", "state": st,
                                                "onboard": rover.onboard()}))
    rover.onboard_label = onboard
    if onboard == "green" and ballcolor is None:
        print("onboard classifier unavailable (ballcolor.py not found): ground guidance only")
    n = [0]

    def grab():
        t_end = time.time() + 0.5
        while latest["n"] == used[0] and time.time() < t_end:
            time.sleep(0.005)
        used[0] = latest["n"]
        frame = latest["f"]
        ok = frame is not None
        if ok and rot is not None:  # upright before the onboard lock and the ground both see it
            frame = cv2.rotate(frame, rot)
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
    # venue TurboPi: camera remounted upright (landscape) at 03:40; 270 undoes a 90 deg clockwise mount
    ap.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                    help="clockwise degrees applied to every frame (270 = undo a 90 deg clockwise mount)")
    ap.add_argument("--hw", default="none", choices=["none", "hiwonder"])
    ap.add_argument("--onboard", default="green", choices=["person", "green", "none"])
    ap.add_argument("--selftest", action="store_true", help="guarded chassis/pan moves, no network")
    ap.add_argument("--probe", action="store_true", help="list the Hiwonder SDK's servo/chassis calls; moves nothing")
    ap.add_argument("--pan-call", default="auto", help="pan servo call fn(id, pulse_us, ms); auto = "
                    "HiwonderSDK.Board:setPWMServoPulse with --hw hiwonder; none = no pan (body steers)")
    # verified on the venue TurboPi (Pi 5 image): servo 1 pans, servo 2 tilts; pulse 1167 (lower)
    # turned the camera to the rover's right, so +deg (right) needs pan-sign -1
    ap.add_argument("--pan-id", type=int, default=1)
    ap.add_argument("--pan-center", type=float, default=1500.0, help="pulse (us) that points straight ahead")
    ap.add_argument("--pan-us-per-deg", type=float, default=11.1)
    ap.add_argument("--tilt-id", type=int, default=2, help="tilt servo (venue TurboPi: 2)")
    # venue TurboPi (upright mount): lower pulse = camera up; 1200-1500 point at the floor,
    # 800-900 is about level; 1000 (slightly down) keeps a close ball in frame on arrival
    ap.add_argument("--tilt-us", type=float, default=1000.0, help="tilt pulse set at start; 0 = leave it")
    ap.add_argument("--trace", action="store_true", help="log every control tick and lock decision")
    ap.add_argument("--pan-sign", type=float, default=-1.0, choices=[1.0, -1.0])
    a = ap.parse_args()
    global TRACE
    TRACE = TRACE or a.trace
    _exit_on_sigterm()
    if a.probe:
        probe()
        return
    pan = None
    if a.pan_call == "auto":
        a.pan_call = "HiwonderSDK.Board:setPWMServoPulse" if a.hw == "hiwonder" else ""
    if a.pan_call == "none":
        a.pan_call = ""
    if a.pan_call:
        pan = PulseServo(PulseServo.resolve(a.pan_call), a.pan_id, a.pan_center,
                         a.pan_us_per_deg, a.pan_sign)
    if pan is not None and a.hw != "hiwonder":
        ap.error("--pan-call needs --hw hiwonder")
    tilt = (pan.fn, a.tilt_id, a.tilt_us) if pan is not None and a.tilt_us > 0 else None
    hw = HiwonderHardware(pan=pan, tilt=tilt) if a.hw == "hiwonder" else NoHardware()
    if a.hw == "hiwonder" and tilt is not None:
        hw.set_tilt(a.tilt_us)   # camera at the start tilt, pan centred
        pan.set(0.0)
    if a.selftest:
        selftest(hw)
        return
    if not a.url:
        ap.error("url is required unless --selftest")
    try:
        asyncio.run(run(a.url, a.camera, hw, a.node, onboard=a.onboard, rotate=a.rotate))
    finally:
        hw.stop()


if __name__ == "__main__":
    main()
