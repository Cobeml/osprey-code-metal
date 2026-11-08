# Hardware — verified state

Measured November 7, 2026 by Claude Code over SSH. Update this file when anything changes.

## Network

```text
MacBook Air (M1, 8 GB)                         Raspberry Pi 5 (16 GB), hostname raspberrypi
  Wi-Fi en0: venue Wi-Fi 10.1.200.x  ─┐          wlan0: venue Wi-Fi 10.1.200.238 (internet uplink)
  en10: Realtek USB GbE 169.254.135.249 ── Ugreen GbE switch ── eth0: 169.254.50.2/16 (static, NetworkManager)
```

- Venue Wi-Fi **isolates clients**: Mac ↔ Pi over Wi-Fi does not work. Use the wired link.
- Pi eth0 is static `169.254.50.2/16` (`Wired connection 1`, `ipv4.method manual`, `ipv6.method link-local`). The Mac self-assigns 169.254.x.x on its adapter, so no Mac config is needed.
- SSH alias on the Mac: `ssh mob-pi` (user `pi`, key `~/.ssh/id_ed25519_cobeml`). `pi` has passwordless sudo.
- The Mac's USB Ethernet only enumerates when plugged directly into the Mac (not through the daisy-chained hub).

## Raspberry Pi 5

| Item | Value |
|---|---|
| OS | Raspberry Pi OS, Debian 13 (trixie), kernel 6.12.47+rpt-rpi-2712, aarch64 |
| Python | 3.13.5 (system), OpenCV 4.10.0 (`python3-opencv`), pyserial 3.5 |
| Hailo | Hailo-8 on PCIe `0001:01:00.0`, `/dev/hailo0`, firmware 4.23.0, `hailo-all` 5.1.1, `hailo_platform` 4.23.0 |
| Hailo-8 models | `/usr/share/hailo-models/`: `yolov8s_h8.hef` (COCO person), `yolov8s_pose_h8.hef`, `yolov6n_h8.hef`, `yolov5n_seg_h8.hef`. Files ending `_h8l`/`_h10` do not run on Hailo-8 |
| Build tools | cmake 3.31, g++ 14.2, libusb-1.0-0-dev, libopencv-dev |
| Thermal/power | 53 °C idle, `throttled=0x0` |

## Aurora 930 (ship deck camera)

- USB `3251:1930`, serial `HY400523001036413G00755`, USB 2.0 (480 Mb/s); plug directly into the Pi. Verified Nov 7 evening through a passive USB extension cable: 14.5–15 fps, no bridge restarts over 30 s.
- Not UVC: needs the Deptrum SDK. Installed udev rule `/etc/udev/rules.d/99-deptrum-libusb.rules` (vendor 3251, mode 0666).
- SDK: Hiwonder Google Drive, `deptrum-ros-driver-aurora930-aarch64-0.7.4-source.tar.gz` (sha256 `4bc2b6bb…be83af8`), extracted at `~/vendor/deptrum/` on the Pi. Library: `ext/deptrum-stream-aurora900-linux-aarch64-v1.1.4/{lib,include}`. C++ only, depends on system libc/libstdc++/libgomp.
- Verified probe: [`native/aurora/aurora_probe.cc`](../native/aurora/aurora_probe.cc) (built at `~/osprey/native/aurora/aurora_probe` on the Pi by `native/aurora/build.sh`; an older copy remains in `~/mob-sar`).

| Mode | Resolution (RGB/IR/depth, aligned) | Measured fps (15 requested) |
|---|---|---|
| 0 | 320×200 | 14.6 |
| 1 | 480×300 | 13.6 |
| 2 | 640×400 | 14.4 |

- RGB is NV12 (12 bpp), IR 8-bit, depth uint16 (mm). Intrinsics at 640×400: fx≈424, fy≈425, cx≈320, cy≈198.
- Depth works ~0.3–3 m indoors; fails near bright windows/sunlight (structured light). Not an outdoor/ocean sensor.
- Was mounted upside down during the test.

## Serial devices

| Port | Device | Notes |
|---|---|---|
| `/dev/ttyUSB0` | Seeeduino v4.2 (ATmega328P, sig `1e950f`) via CP2102N, on Sabrent hub | Optiboot at 115200 responds; current sketch prints nothing; no Grove sensors attached |
| — | XIAO ESP32-C5 | Powers on (charge LED) but never enumerates on any port: almost certainly a charge-only cable. Expect `303a:*` on `/dev/ttyACM0` once a data cable is used |

## TurboPi rover (Scout B), verified Nov 8 ~02:50

- Raspberry Pi 5 running Hiwonder's Pi 5 / ROS 2 image (Debian 12, Python 3.11.2, OpenCV 4.6).
  `ssh turbopi` = `pi@169.254.50.3` (key `id_ed25519_cobeml`, passwordless sudo). Its eth0
  "Wired connection 1" had no IPv4 and kept dropping; set to manual `169.254.50.3/16`,
  ipv6 link-local. Its wlan0 is Hiwonder's own hotspot (`hiwonder-ap`, 192.168.149.1); no internet.
- No host `HiwonderSDK`: the board is `~/board_demo/ros_robot_controller_sdk.py` on `/dev/rrc`
  (= `ttyAMA0`, 1 Mbaud). `turbopi/HiwonderSDK/` is our shim over it (chassis + pan servo).
- Hiwonder's ROS 2 container (`turbopi`, started by `start_node.service`) holds `/dev/ttyAMA0`
  and `/dev/video0`: stop it before running our client (`sudo systemctl stop start_node;
  docker stop turbopi`); it comes back on reboot (`docker start turbopi` to restore sooner).
- Self-test passed: forward, backward, spin clockwise and anticlockwise all correct
  (`set_velocity` yaw > 0 = clockwise). Pan = PWM servo 1 (servo 2 tilts); a lower pulse turns
  the camera to the rover's right, so pan-sign -1. Camera 640x480 on `/dev/video0`, mounted turned
  90 deg clockwise: the client rotates frames 270 (portrait 480x640).
- Battery 7.58 V at 02:30 (2S pack: 8.4 V full, ~6.8 V low). No RTC/NTP: the clock was 89 days
  behind; set from the Mac with `sudo date -s @<epoch>` (repeat after a reboot).
- websockets 17.4 copied from the Mac venv into `~/osprey-rover/` (pure Python fallback).

## Not yet set up

- Phone scout: `cloudflared` 2026.10.7 installed on the Pi (arm64 .deb from Cloudflare GitHub releases, sha256 d9407eb6…6bf836); tunnel not yet tested with the phone.
- Any aircraft.
