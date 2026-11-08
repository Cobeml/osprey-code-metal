"""Show what a Qorvo DWM3001CDK prints, and the ranges Osprey would read from it.

    python3 turbopi/uwb_probe.py                       list USB serial ports
    python3 turbopi/uwb_probe.py auto                  read the first port for 10 s
    python3 turbopi/uwb_probe.py /dev/cu.usbmodemXXXX --send HELP
    python3 turbopi/uwb_probe.py PORT --send RESPF     start ranging as the responder (ball)
    python3 turbopi/uwb_probe.py PORT --send INITF     start ranging as the initiator (rover)

--send can be repeated (e.g. --send RESPF --send SAVE). Reads only otherwise; moves nothing.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uwb  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("port", nargs="?")
    ap.add_argument("--send", action="append", default=[], help="command line to send, e.g. HELP / INITF / RESPF")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args()
    ports = uwb.find_ports()
    if not a.port:
        print("USB serial ports:", ports or "none (plug the board in; try its other USB socket)")
        return
    port = ports[0] if a.port == "auto" and ports else a.port
    if port == "auto":
        sys.exit("no USB serial port found")
    fd = uwb.open_raw(port, a.baud)
    print(f"reading {port} for {a.seconds:.0f} s (Ctrl-C stops)")
    ranges, buf = [], b""
    t0 = time.time()
    try:
        os.write(fd, b"\r\n")
        time.sleep(0.3)
        for cmd in a.send:
            print(f">>> {cmd}")
            os.write(fd, (cmd + "\r\n").encode())
            time.sleep(0.5)
        while time.time() - t0 < a.seconds:
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                time.sleep(0.02)
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("utf-8", "replace").rstrip()
                r = uwb.parse_range_m(line)
                if r is not None:
                    ranges.append(r)
                print(f"{time.time() - t0:6.2f}  {line}" + (f"   -> {r:.2f} m" if r is not None else ""))
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)
    if ranges:
        ranges.sort()
        print(f"\n{len(ranges)} ranges, median {ranges[len(ranges) // 2]:.2f} m, "
              f"{len(ranges) / max(1e-6, time.time() - t0):.1f} Hz")
    else:
        print("\nno ranges parsed: paste the lines above to Claude (the parser may need this firmware's format)")


if __name__ == "__main__":
    main()
