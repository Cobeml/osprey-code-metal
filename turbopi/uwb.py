"""UWB range from a Qorvo DWM3001CDK on USB serial (two-way ranging, distance only).

One board rides on the rover (initiator), one sits with the ball (responder, "the person's
beacon"). The rover reads ranges from /dev/ttyACM* in a background thread and the controller asks
`range_m()`: the median of the last few readings, or None when stale. No angle: one antenna each,
the camera supplies the direction.

The exact output depends on the firmware the kit ships with, so the parser accepts the common
shapes and ignores anything else:
  Qorvo CLI (FiRa) JSON  {"Block":12, "results":[{"Addr":"0x0001","Status":"Ok","D_cm":123, ...}]}
  key/value text         DIST: 1.23 m   distance=123cm   range: 1230 mm   D_cm: 123
Unknown lines are kept in `tail` so `uwb_probe.py` can show what the board really prints.

No pyserial needed: USB CDC ports are opened raw with termios (baud is nominal on CDC, set anyway).
"""
from __future__ import annotations

import glob
import json
import os
import re
import statistics
import threading
import time
from collections import deque
from typing import Optional

MAX_RANGE_M = 200.0
STALE_S = 0.6            # newest reading older than this: no range
WINDOW = 5               # median of this many readings (UWB spikes on body blockage)

_CM_KEYS = ("d_cm", "distance_cm", "dist_cm", "range_cm")
_MM_KEYS = ("d_mm", "distance_mm", "dist_mm", "range_mm")
_M_KEYS = ("distance_m", "dist_m", "range_m", "d_m", "distance", "dist", "range")
_TEXT = re.compile(r"(?i)\b(d_cm|d_mm|d_m|dist(?:ance)?(?:_cm|_mm|_m)?|range(?:_cm|_mm|_m)?)\"?\s*[:=]\s*"
                   r"(-?\d+(?:\.\d+)?)\s*(cm|mm|m)?\b")
_BAD_STATUS = re.compile(r"(?i)\"?status\"?\s*[:=]\s*\"?(?!ok\b|success\b)([a-z_]+)")


def _unit_value(key: str, value: float, unit: Optional[str]) -> float:
    k = key.lower()
    unit = (unit or "").lower()
    if unit == "cm" or k.endswith("_cm"):
        return value / 100.0
    if unit == "mm" or k.endswith("_mm"):
        return value / 1000.0
    return value


def _from_json(obj) -> Optional[float]:
    """First distance in a JSON object tree whose Status (if any) is OK."""
    if isinstance(obj, dict):
        lower = {str(k).lower(): v for k, v in obj.items()}
        status = lower.get("status")
        ok = status is None or str(status).lower() in ("ok", "success", "0")
        if ok:
            for keys, scale in ((_CM_KEYS, 0.01), (_MM_KEYS, 0.001), (_M_KEYS, 1.0)):
                for k in keys:
                    v = lower.get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        return float(v) * scale
        for v in obj.values():
            r = _from_json(v)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _from_json(v)
            if r is not None:
                return r
    return None


def parse_range_m(line: str) -> Optional[float]:
    """Distance in metres from one line of board output, or None."""
    line = line.strip()
    if not line:
        return None
    r = None
    i = line.find("{")
    if i >= 0:
        try:
            r = _from_json(json.loads(line[i:]))
        except ValueError:
            r = None
    if r is None:
        if _BAD_STATUS.search(line):
            return None
        m = _TEXT.search(line)
        if m:
            r = _unit_value(m.group(1), float(m.group(2)), m.group(3))
    if r is None:
        return None
    if -0.3 <= r < 0:      # TWR reads slightly negative at contact
        r = 0.0
    return r if 0.0 <= r <= MAX_RANGE_M else None


def find_ports() -> list:
    """USB CDC serial ports: /dev/ttyACM* (Linux), /dev/cu.usbmodem* (macOS)."""
    return sorted(glob.glob("/dev/ttyACM*")) + sorted(glob.glob("/dev/cu.usbmodem*"))


def open_raw(port: str, baud: int = 115200) -> int:
    import termios
    import tty

    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    tty.setraw(fd)
    attrs = termios.tcgetattr(fd)
    speed = getattr(termios, f"B{baud}", termios.B115200)
    attrs[4] = attrs[5] = speed
    attrs[2] |= termios.CLOCAL | termios.CREAD
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


class UwbRanger:
    """Background reader. port: a device path or "auto" (first USB CDC port that ranges)."""

    def __init__(self, port: str = "auto", init_cmd: Optional[str] = None, offset_m: float = 0.0,
                 baud: int = 115200, window: int = WINDOW, stale_s: float = STALE_S):
        self.port, self.init_cmd, self.offset_m, self.baud = port, init_cmd, offset_m, baud
        self.stale_s = stale_s
        self.samples: deque = deque(maxlen=window)   # (ts, metres)
        self.tail: deque = deque(maxlen=20)          # last raw lines, for diagnosis
        self.status = "starting"
        self.active_port: Optional[str] = None
        self.count = 0
        self._stop = False

    # ------------------------------------------------------------ readings
    def feed(self, line: str, ts: Optional[float] = None) -> Optional[float]:
        self.tail.append(line.rstrip())
        r = parse_range_m(line)
        if r is not None:
            r = max(0.0, r - self.offset_m)
            self.samples.append((time.time() if ts is None else ts, r))
            self.count += 1
            self.status = "ranging"
        return r

    def range_m(self, now: Optional[float] = None) -> Optional[float]:
        now = time.time() if now is None else now
        if not self.samples or now - self.samples[-1][0] > self.stale_s:
            return None
        recent = [m for t, m in self.samples if now - t <= self.stale_s * 3]
        return statistics.median(recent) if recent else None

    # ------------------------------------------------------------ serial
    def start(self) -> "UwbRanger":
        threading.Thread(target=self._run, daemon=True, name="uwb").start()
        return self

    def stop(self) -> None:
        self._stop = True

    def _candidates(self) -> list:
        return find_ports() if self.port == "auto" else [self.port]

    def _run(self) -> None:
        while not self._stop:
            ports = self._candidates()
            if not ports:
                self.status = "no port"
                time.sleep(2.0)
                continue
            for port in ports:
                if self._stop:
                    return
                self._read_port(port, give_up_s=None if self.port != "auto" else 6.0)
            time.sleep(1.0)

    def _read_port(self, port: str, give_up_s: Optional[float]) -> None:
        try:
            fd = open_raw(port, self.baud)
        except OSError as e:
            self.status = f"open failed: {e.strerror}"
            return
        self.active_port = port
        self.status = "no ranges yet"
        t_open = last_range = time.time()
        sent = False
        buf = b""
        try:
            while not self._stop:
                if self.init_cmd and not sent and time.time() - t_open > 0.5:
                    os.write(fd, (self.init_cmd.strip() + "\r\n").encode())
                    sent = True
                try:
                    chunk = os.read(fd, 4096)
                except BlockingIOError:
                    chunk = b""
                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        raw, buf = buf.split(b"\n", 1)
                        if self.feed(raw.decode("utf-8", "replace")) is not None:
                            last_range = time.time()
                    if len(buf) > 8192:
                        buf = b""
                else:
                    time.sleep(0.01)
                if give_up_s is not None and time.time() - last_range > give_up_s:
                    self.status = f"no ranges on {port}"
                    return       # auto: try the next port
        except OSError as e:     # unplugged
            self.status = f"lost {port}: {e.strerror}"
        finally:
            os.close(fd)
            self.active_port = None
