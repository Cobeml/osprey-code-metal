"""Grove water sensor on the Seeeduino (native/water_probe), read over USB serial.

The sketch prints "A a0 a1 a2 a3 D d2 d3 d4 d5 d6 d7 d8" at 4 Hz. The sensor's SIG goes LOW
when water bridges its traces. Runs in a thread; reconnects when the board is unplugged.
"""
from __future__ import annotations

import glob
import logging
import threading
import time
from typing import Callable, Optional

log = logging.getLogger("osprey.water")


def parse_line(line: str, pin: int, active_low: bool = True) -> Optional[bool]:
    """Wet/dry from one sketch line, None if the line isn't a reading."""
    parts = line.split()
    if len(parts) != 13 or parts[0] != "A" or parts[5] != "D" or not 2 <= pin <= 8:
        return None
    try:
        v = int(parts[6 + pin - 2])
    except ValueError:
        return None
    return (v == 0) if active_low else (v == 1)


class WaterSensor:
    def __init__(self, port: str = "auto", pin: int = 5, active_low: bool = True,
                 on_change: Optional[Callable[[bool], None]] = None):
        self.port_cfg, self.pin, self.active_low = port, pin, active_low
        self.on_change = on_change
        self.wet: Optional[bool] = None   # None = no reading yet / sensor offline
        self.ts: Optional[float] = None    # last reading (monotonic)
        self.changed_ts: Optional[float] = None
        self.status = "starting"
        self.port: Optional[str] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def find_port(self) -> Optional[str]:
        if self.port_cfg not in ("", "auto"):
            return self.port_cfg
        hits = sorted(glob.glob("/dev/serial/by-id/*CP2102N*"))
        return hits[0] if hits else None

    @property
    def online(self) -> bool:
        return self.ts is not None and time.monotonic() - self.ts < 2.0

    def start(self) -> None:
        if self.port_cfg == "off":
            self.status = "off"
            return
        self._thread = threading.Thread(target=self._run, name="water", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _set(self, wet: bool) -> None:
        self.ts = time.monotonic()
        if wet != self.wet:
            self.wet, self.changed_ts = wet, self.ts
            log.warning("water sensor: %s", "WET" if wet else "dry")
            if self.on_change:
                self.on_change(wet)

    def _run(self) -> None:
        try:
            import serial  # pyserial (system package on the Pi)
        except ImportError:
            self.status = "pyserial missing"
            return
        while not self._stop.is_set():
            port = self.find_port()
            if not port:
                self.status, self.wet = "no sensor board on USB", None
                self._stop.wait(2.0)
                continue
            try:
                # don't toggle DTR: opening would otherwise reset the board (2 s of no data)
                with serial.Serial() as s:
                    s.port, s.baudrate, s.timeout, s.dtr = port, 115200, 1.0, False
                    s.open()
                    self.port, self.status = port, "connected"
                    while not self._stop.is_set():
                        raw = s.readline()
                        if not raw:
                            continue
                        wet = parse_line(raw.decode(errors="replace"), self.pin, self.active_low)
                        if wet is not None:
                            self.status = "ok"
                            self._set(wet)
            except Exception as e:  # noqa: BLE001
                self.status, self.wet = f"serial error: {e.__class__.__name__}", None
                self._stop.wait(2.0)
