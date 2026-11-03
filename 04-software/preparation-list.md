# Software to prepare before arrival

**Prepare Python, Arduino tooling, serial communication and a local data/display path first.** Add one camera, radio or robot stack after choosing a project and confirming its hardware. This is a researched preparation list, not an installed-software inventory. Sources were checked on 2026-10-29; release compatibility must be checked again against the supplied images.

Priority means **P0: prepare for nearly any project**, **P1: needed for the selected branch**, **P2: defer unless the idea specifically requires it**. Mac is the current laptop assumption. Linux hardware drivers belong on the Pi/Jetson or a matching development environment, even when the Mac and target both have ARM processors.

## P0: arrive with these ready

| Tool and official source | Why you need it | Where/language | Preparation and proof |
|---|---|---|---|
| [Git](https://git-scm.com/downloads/) and familiar editor | Recover working versions and collaborate | Mac/target; basic shell | Verify version and author identity; make a local first commit in the starter. No new IDE required |
| [Python 3, venv and pip](https://docs.python.org/3/tutorial/venv.html) | Main integration language for parsing, logging and local services | Mac simulation; target Linux adapters | Use a version supported by chosen SDKs, create environment, parse sample JSON; cache tested dependencies |
| [Arduino IDE 2](https://github.com/arduino/arduino-ide) | Guaranteed controller is Arduino-compatible; upload/serial monitor in one tool | Mac host; C/C++ firmware | Download [official installer](https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing); exact board core and Grove libraries await model IDs. Compile its basic example before arrival if identified |
| [pySerial](https://github.com/pyserial/pyserial) | Easiest initial controller-to-Pi link | Python on Mac/Linux; BSD | Install in environment, enumerate ports, later read/reconnect a real board. No ports without hardware is normal |
| [SQLite](https://sqlite.org/whentouse.html) through Python `sqlite3` | Durable local observations and outgoing queue without a database server | Mac/Pi; Python/SQL; core [public domain](https://sqlite.org/copyright.html) | Store/reload one record and test restart. Separate delivery state from human review |
| [Pi Imager and OS downloads](https://www.raspberrypi.com/software/) plus saved setup docs | Recovery option for the guaranteed Pi | Imager on Mac; OS on Pi | Obtain organizer-approved image and storage details. Preserve and boot the supplied working image first |

The starter deliberately has no application dependencies yet. A simple local browser page can be the first interface; choose its framework when coding starts. SSH and basic shell use—directories, processes, logs and copying files—will be more immediately useful than learning another language. [Pi remote access](https://www.raspberrypi.com/documentation/computers/remote-access.html)

## P1: select the branch you actually need

| Branch/tool | Why and target | What to obtain and verify |
|---|---|---|
| Vision: [OpenCV](https://github.com/opencv/opencv) | Capture, resize, annotate and replay frames; Python/C++ on Mac and Linux; Apache-2.0 core | Packaged compatible release plus local sample video. Decode/save one frame before adding AI |
| Pi camera: [Picamera2](https://github.com/raspberrypi/picamera2) | Python interface to Pi camera stack; BSD-2-Clause | Pi OS target, normally OS `apt` installation to align libcamera. Not a native Mac camera SDK; USB cameras have another path |
| Accelerator: [Hailo Apps](https://github.com/hailo-ai/hailo-apps) and [Pi AI setup](https://www.raspberrypi.com/documentation/computers/ai.html) | Vendor examples for supported local inference; Python/C++/GStreamer; Apps repo MIT | Confirm accelerator/OS first; cache matching runtime, example, clip and compiled model. Vendor firmware/model/compiler terms are separate |
| CPU fallback: [ONNX Runtime](https://github.com/microsoft/onnxruntime) | Portable inference and laptop replay; Python/C++; MIT runtime | Small compatible model with separately checked weights license; measure actual frame latency |
| Exact sensors: [Seeed Grove docs](https://wiki.seeedstudio.com/Grove_System/) | Correct wiring and module driver; usually Arduino C/C++ | Module SKU, voltage, interface, vendor example and its dependencies; Grove is not one universal driver |
| Wireless controller: [ESP32 Arduino core](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html) | Reuse Arduino workflow for an ESP32 node | Official stable board package for exact variant, serial example and needed libraries. Use [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html) only if fuller firmware control is needed |
| Depth: [RealSense](https://github.com/realsenseai/librealsense) **or** [DepthAI](https://github.com/luxonis/depthai-core) | Vendor-specific RGB/depth access; Python/C++ | Wait for camera SKU. Match SDK/API/firmware generation; verify known-distance measurement and alignment. Prefer supported Linux target for RealSense |
| Multiple event producers: [Mosquitto](https://github.com/eclipse-mosquitto/mosquitto) + [Paho Python](https://github.com/eclipse-paho/paho.mqtt.python) | Local MQTT broker/client decouple adapters and consumers; EPL/EDL licensing | Broker on Mac or Pi; Python client. Cache selected versions; use current callback API and test reconnect/dedupe. Configure listeners/access explicitly |
| Visual integration alternative: [Node-RED](https://github.com/node-red/node-red) + [FlowFuse Dashboard](https://github.com/FlowFuse/node-red-dashboard) | Fast flows and local widgets instead of a custom UI; Node.js/JavaScript; Apache-2.0 | Cache runtime, nodes and exported flows. Current guidance recommends Node 24.x; Node-RED 5.x requires at least 22. Keep editor local or configure authentication |
| Offline map: [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) + [PMTiles](https://github.com/protomaps/PMTiles) | Local browser map with regional archive; JavaScript/TypeScript; implementations BSD-3-Clause | Cache JS/CSS, styles, glyphs, sprites and licensed tiles; local server needs required range reads. Cold-load and pan/zoom offline |
| Off-grid alerts: [Meshtastic firmware](https://github.com/meshtastic/firmware) + [Python client](https://github.com/meshtastic/python) | Existing LoRa messaging; firmware C/C++, client Python; GPL-3.0 repositories | Requires at least two suitable compatible radios for a link. Cache firmware for actual board; align permitted region, radio/channel settings and team access configuration |

Node version and access guidance: [Node-RED versions](https://nodered.org/docs/faq/node-versions), [editor security](https://nodered.org/docs/user-guide/runtime/securing-node-red). Mapping dependencies: [PMTiles integration](https://docs.protomaps.com/pmtiles/maplibre). Radio compatibility: [Meshtastic supported hardware](https://meshtastic.org/docs/hardware/devices/).

## P2: useful tools that can consume the event

| Tool | Use only when | Main preparation constraint |
|---|---|---|
| [ROS 2](https://www.openrobotics.org/blog/2024/5/ros-jazzy-jalisco-released), RViz, [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox), [Nav2](https://docs.nav2.org/) | A selected robot already uses ROS, or mapping/navigation is the core project | Match the robot's distribution and drivers. Jazzy/Ubuntu 24.04 is a supported pairing, not a “latest” claim. Pi OS/macOS are not interchangeable Ubuntu apt targets. Python/C++ plus configuration |
| [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) / [PX4 simulation](https://docs.px4.io/main/en/dev_setup/dev_env_mac), or [Crazyflie library](https://github.com/bitcraze/crazyflie-lib-python) | Exact programmable drone and control ecosystem are confirmed | Simulate telemetry first; radio/server binaries and physical flight procedures differ. FPV alone implies no SDK |
| [NVIDIA JetPack](https://developer.nvidia.com/embedded/jetpack) | A particular Jetson is allocated | Use its compatible supplied image. Generic Mac CUDA installation is not preparation for Jetson. Python/C++, vendor-specific stack terms |
| [GPSD](https://gpsd.io/) | A GNSS receiver needs a shared/replayable position feed | Check receiver support and target Linux setup; show fix validity/age; verify selected release notices |
| [GNU Radio](https://github.com/gnuradio/gnuradio) | The project explicitly requires SDR/DSP and someone owns it | Python/C++ flowgraphs plus model-specific radio drivers; GPL-3.0. A spectrum display is not person localization |
| [TAK Server](https://github.com/TAK-Product-Center/Server) | A real responder/client integration is part of judging | Confirm receiver/version first; server setup includes Java, database and certificates. Review notices; prove actual event acceptance |

## Compatibility traps to resolve before downloading large stacks

**Hailo generations:** the reviewed [Model Zoo](https://github.com/hailo-ai/hailo_model_zoo) directs Hailo-8/8L to **v2.x with Dataflow Compiler v3.x**; default master targets Hailo-10/15. The current [Pi AI page](https://www.raspberrypi.com/documentation/computers/ai.html) specifies 64-bit Pi OS Trixie and different, mutually exclusive package families for Hailo-8 versus Hailo-10H. Prefer an organizer-provided compiled model; native Mac compiler support was not established.

**Camera generations:** [RealSense macOS instructions](https://github.com/realsenseai/librealsense/blob/master/doc/installation_osx.md) currently exclude Viewer and disable motion sensors; [release notes](https://github.com/realsenseai/librealsense/releases) describe platform limitations. DepthAI examples must match OAK/API generation. Thermal and LiDAR SDKs are equally model-specific: [MLX90640 driver](https://github.com/adafruit/Adafruit_CircuitPython_MLX90640) and [SLAMTEC ROS 2 driver](https://github.com/Slamtec/sllidar_ros2) are examples, not universal drivers.

**Code versus model licenses:** a permissive runtime does not license downloaded weights, datasets or map tiles. [Ultralytics](https://www.ultralytics.com/license) offers AGPL-3.0 and Enterprise terms covering software/models; exporting weights does not erase their obligations. Review the selected model's terms before incorporating it. The starter intentionally selects no project license or detector.

## What to learn and what to save

Learn **Python first**, enough **Arduino C/C++** to sample, serialize and handle timeouts, then **shell/SSH**. Learn **JavaScript/TypeScript** when a custom browser map/UI needs it. SQL basics help inspect local events. Rust, CUDA C++, advanced robotics and RF programming are optional, not prerequisites.

For each selected dependency, save the official URL, release/tag, target OS/architecture, license, installer/package and working example. Save board cores, firmware, model weights and map assets separately; a repository clone does not include all of them. Mac ARM packages are not Linux ARM packages. Download only after choosing a compatible combination and retain checksums where provided.

Official owners, support matrices, public licenses and release channels are trust signals, not a security audit. [Picamera2](https://github.com/raspberrypi/picamera2/releases), [Hailo Apps](https://github.com/hailo-ai/hailo-apps/releases) and [ESP32 core](https://github.com/espressif/arduino-esp32/releases) expose release histories. pySerial's slower [release cadence](https://github.com/pyserial/pyserial/releases) still warrants a local OS smoke test. No universal version lock has been tested; record pins after the actual stack works.

Continue with the [preflight checklist](preflight-checklist.md).
