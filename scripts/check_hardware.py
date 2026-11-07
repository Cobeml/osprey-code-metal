#!/usr/bin/env python3
"""Pass/fail table for the Pi's hardware. Run on the Pi: python3 scripts/check_hardware.py"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def check_hailo():
    rc, out = run("hailortcli fw-control identify")
    ver = next((line.split(":", 1)[1].strip() for line in out.splitlines() if "Firmware Version" in line), "")
    return rc == 0, ver or out.strip()[-80:]


def check_hef():
    p = "/usr/share/hailo-models/yolov8s_h8.hef"
    return os.path.exists(p), p


def check_aurora_usb():
    rc, out = run("lsusb -d 3251:1930")
    return rc == 0 and "3251:1930" in out, out.strip() or "not found"


def check_aurora_stream():
    probe = os.path.join(ROOT, "native/aurora/aurora_probe")
    if not os.path.exists(probe):
        return False, "probe not built (native/aurora/build.sh)"
    out_dir = os.path.join(ROOT, "runtime/probe")
    os.makedirs(out_dir, exist_ok=True)
    rc, out = run(f"{probe} 2 10 30 {out_dir}", timeout=40)
    fps = next((line for line in out.splitlines() if line.startswith("frames=")), out.strip()[-80:])
    return rc == 0, fps


def check_serial():
    ports = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    return bool(ports), " ".join(ports) or "none (optional)"


def check_cloudflared():
    rc, out = run("cloudflared --version")
    return rc == 0, out.strip().splitlines()[0] if rc == 0 else "not installed"


def check_throttle():
    rc, out = run("vcgencmd get_throttled")
    return rc == 0 and "0x0" in out, out.strip()


CHECKS = [
    ("Hailo-8 identify", check_hailo, True),
    ("yolov8s_h8.hef", check_hef, True),
    ("Aurora USB 3251:1930", check_aurora_usb, True),
    ("Aurora stream (mode 2)", check_aurora_stream, True),
    ("Power/throttling", check_throttle, True),
    ("cloudflared", check_cloudflared, False),
    ("Serial ports", check_serial, False),
]


def main():
    failed = 0
    for name, fn, required in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, repr(e)
        mark = "PASS" if ok else ("FAIL" if required else "warn")
        failed += (not ok) and required
        print(f"{mark:4}  {name:24} {detail}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
