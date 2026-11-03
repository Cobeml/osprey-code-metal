# Compute vision and robotics software readiness

Research checked 2026-10-29. Scope: computer, microcontroller, camera, sensor, robot and drone tooling. Wireless, dashboard and offline mapping software are covered by the companion research. This is a documentation review: no packages installed and no supplied hardware tested. The PDF specifies families, not most model numbers; all model-specific recommendations below are conditional.

## What should be prepared before arrival and how badly is it needed?

### Takeaway

Prepare a small Python-and-Arduino foundation on the Mac, preserve the organizers' supplied Pi image, and add one hardware-specific stack after the actual device is identified. Robotics navigation, custom model compilation and Jetson reimaging are optional project branches, not prerequisites for a strong demo.

### Cited Findings

Priority definitions are recommendations: **P0 = prepare before arriving regardless of idea; P1 = prepare if selecting that project branch; P2 = optional specialist work; defer = insufficient hardware information.** The smoke tests are proposed acceptance checks, not tests already executed.

| Priority | Tool / official upstream | Why it earns its place | Where / language | Before arrival and first proof |
|---|---|---|---|---|
| P0 | Git and an editor already familiar to the team; [Git downloads](https://git-scm.com/downloads/) | Keep a recoverable baseline and share changes; avoids merging files by hand. | Mac and Pi; shell usage rather than a new language. | Verify `git --version`, create a local commit, and practice branch/restore in the starter repo. No need to adopt a new IDE. |
| P0 | Python 3, `venv`, `pip`; [official environment guide](https://docs.python.org/3/tutorial/venv.html) | Main glue language for sensor parsing, logging, detection and local services. Environments isolate dependencies. | Mac for simulation; Linux target for hardware adapters. | Create a dedicated environment, run a JSON parsing script, cache dependencies only after a successful install. Use a supported Python version shared by chosen SDKs rather than automatically choosing newest Python. |
| P0 | [Arduino IDE 2](https://github.com/arduino/arduino-ide), [official install guide](https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing) | The guaranteed microcontroller is Arduino-compatible. IDE provides board/library management, upload and serial monitor. | Mac host compiles C/C++ sketches for microcontroller. | Download IDE now. Obtain exact board name, install its board package and required sensor libraries before losing Internet. Compile Blink first; physical upload awaits hardware. IDE source is AGPL-3.0; libraries and board cores have their own licenses. |
| P0 | [pySerial](https://github.com/pyserial/pyserial) | Simple link between Arduino USB serial and a Python application; avoids ROS for basic sensor data. | Python; macOS, Linux, Windows supported; BSD license. | Install `pyserial` in environment; run `python -m serial.tools.list_ports`. No port present is expected without a board. At event, read a newline-delimited JSON sensor message and reconnect after unplugging. |
| P0 | [Raspberry Pi Imager / Pi OS download](https://www.raspberrypi.com/software/) | Recovery preparation for guaranteed Pi, not a reason to overwrite its working setup. | Imager on Mac; OS runs on Pi. | Download Imager and organizer-approved 64-bit image; bring SD reader if needed. Ask whether storage is preflashed. Boot provided image first. |
| P1 for camera project | [OpenCV](https://github.com/opencv/opencv) | Frame capture, image resizing, drawing detection boxes, video replay and conventional vision. | Python/C++; Mac replay, Pi/Jetson deployment. Apache-2.0 core. | Install a compatible packaged release, decode a short local test video and save one annotated frame. Freeze package version; do not build repository default branch just because it is newest. |
| P1 for Pi CSI camera | [Picamera2](https://github.com/raspberrypi/picamera2) and Pi camera utilities | Supported Python interface to Pi's libcamera stack. A USB camera may instead use OpenCV/V4L2. | Pi OS target, Python; BSD-2-Clause. Not a Mac camera SDK. | Read examples now. Install with OS `apt` on Pi if missing so libcamera dependencies match. First show a camera preview/captured still before adding inference. |
| P1 for accelerated vision | [Hailo Apps](https://github.com/hailo-ai/hailo-apps), [official Pi AI setup](https://www.raspberrypi.com/documentation/computers/ai.html) | Vendor examples offer a shorter route to person detection than custom compilation. Conditional on confirmed Hailo hardware. | Pi Linux; Python/C++, GStreamer. Apps repo MIT; entire vendor/model stack has separate terms. | Cache exact compatible release, sample clip and precompiled model after device/OS confirmation. First run `hailortcli fw-control identify`, then vendor video example. Do not assume a new ONNX model will run directly on accelerator. |
| P1 for CPU fallback | [ONNX Runtime](https://github.com/microsoft/onnxruntime) | Portable inference fallback when accelerator setup fails; useful for replay on laptop. | Python/C++; cross-platform; MIT runtime. | Choose a compatible small ONNX model with a separately checked weight license. Run one frame and measure latency. CPU performance does not establish Pi NPU performance. |
| P1 if ESP32 selected | [Espressif Arduino core](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html), [upstream releases](https://github.com/espressif/arduino-esp32/releases) | Reuses Arduino workflow for a wireless sensor node. | Mac host; C/C++ firmware. | Add official stable Boards Manager URL, install core, then select exact ESP32 variant. Compile Blink and serial output. Chip families differ; do not assume all ESP32s share Bluetooth/radio capabilities. |
| P1 after exact sensor selection | [Seeed Grove documentation](https://wiki.seeedstudio.com/Grove_System/) and module-specific vendor library | Grove is a connector ecosystem, not one universal SDK. Wrong driver or voltage can waste the event. | Usually Arduino C/C++; some Pi Python drivers. | Record module SKU, interface, voltage and library. Download its official example and dependencies. Run a raw-reading example before threshold or sensor fusion logic. |
| P1 if depth camera selected | [RealSense SDK](https://github.com/realsenseai/librealsense) **or** [Luxonis DepthAI](https://github.com/luxonis/depthai-core) | Depth SDK must match camera vendor/model; neither is a universal depth driver. | Python/C++; prefer supported Linux target for RealSense. | Wait for SKU. Then cache exact SDK/firmware-compatible release and viewer/sample. Prove RGB and depth alignment plus metric distance on a known target. |
| P2; P1 only for a robot already using ROS | ROS 2 + RViz, then [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox) / [Nav2](https://docs.nav2.org/) | Middleware, inspection, mapping and navigation; valuable when robot drivers already exist, disproportionate overhead for a standalone sensor box. | Linux target, Python/C++; YAML config. | Ask the robot's existing ROS distribution. Jazzy/Ubuntu 24.04 is a conservative supported pairing, not an assertion it is newest. Use a matching VM/container for simulation if needed; native Mac/USB/DDS behavior requires testing. |
| P2; P1 only for confirmed compatible drone | [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) + PX4 simulator; or [Crazyflie Python library](https://github.com/bitcraze/crazyflie-lib-python) | Drone families expose different control APIs. FPV does not imply a programmable MAVLink autopilot. | Python client; flight stack remains onboard. | Ask exact drone and radio adapter first. Practice simulator telemetry, then vendor supervised procedures. Never assume generic takeoff script works on every drone. |
| P2; defer until Jetson model known | [NVIDIA JetPack](https://developer.nvidia.com/embedded/jetpack) | Correct CUDA/TensorRT/camera environment for a checked-out Jetson. | Jetson Linux target; Python/C++. NVIDIA stack includes vendor-specific terms. | Preserve organizer image, record Jetson model and JetPack version, run supplied demo. Do not preinstall a generic desktop CUDA package on the Mac or assume one JetPack release supports every old board. |

### Inferences

- This table can be reduced to the first five rows for universal laptop readiness; OpenCV plus one inference route is the next useful branch. The recommendations are based on the guaranteed Pi/Arduino kit and the documented support paths, not a measured comparison of installation times.
- Prefer Python for high-level code and enough Arduino C++ to read sensors, implement a timeout and serialize a record. Learn shell basics (`cd`, virtual environments, SSH, process logs) next. JavaScript/TypeScript is useful only for a browser interface. Rust, CUDA C++ and custom FPGA-style work are not required to begin; adopt them only if teammates already know them and a concrete need emerges.
- A robust baseline is Arduino → USB serial → Python on Pi → timestamped events → local UI. This avoids making access to shared robotics or custom AI compilation critical to the demo.
- For every downloaded dependency, record upstream URL, tag/version, license and target architecture. Cache source alone is insufficient: build toolchains, Python wheels, board packages, model weights and simulator assets may be separate downloads.

### Gaps

- Exact microcontroller, Grove kit contents, camera SKUs, accelerator, robot, drone, target OS images and driver versions are absent from the attachment. Final board-package and SDK pins cannot be honestly supplied yet.
- No live installation or ARM64 wheel compatibility test was performed. Proposed smoke checks must be run before claiming readiness.
- The laptop model/CPU architecture was not requested or verified; Mac preparation is inferred from the workspace, not a guarantee of which laptop attends.

## Which compatibility and trust decisions matter most?

### Takeaway

“Open source” and “runs Python” do not imply compatible hardware or unrestricted model rights. Use vendor-owned repositories and tested package sets, then pin the versions that actually work.

### Cited Findings

- The official Pi AI page currently specifies 64-bit Pi OS Trixie. Hailo-8 family uses `hailo-all`, while Hailo-10H uses `hailo-h10-all`; packages cannot coexist. Dependencies include firmware, kernel driver, HailoRT and Tappas. This supports waiting for the exact organizer image rather than blindly following an older tutorial. [Pi AI documentation](https://www.raspberrypi.com/documentation/computers/ai.html)
- **Critical Hailo repository trap:** Hailo-8 and Hailo-8L use Model Zoo **v2.x** with Dataflow Compiler **v3.x**; default master is for Hailo-10/15. The model compiler produces HEF executables. Use an appropriate precompiled model for a first demo and defer custom compilation. [Hailo Model Zoo compatibility notice](https://github.com/hailo-ai/hailo_model_zoo)
- Hailo Apps distinguishes GenAI apps for Hailo-10H from vision pipelines and standalone HailoRT examples. Therefore do not promise that the unspecified 26-TOPS device runs the latest LLM demos. [Hailo Apps](https://github.com/hailo-ai/hailo-apps)
- Picamera2 recommends `apt` rather than independent `pip` installation to keep libcamera versions aligned; official support is Raspberry Pi OS. It is a replacement for legacy Picamera. [Picamera2 installation](https://github.com/raspberrypi/picamera2)
- ROS Jazzy has Tier-1 Ubuntu 24.04 support for ARM64 and AMD64; matching Ubuntu in a VM or target Linux is a clearer preparation path than treating Pi OS or macOS as equivalent apt targets. [Open Robotics Jazzy announcement](https://www.openrobotics.org/blog/2024/5/ros-jazzy-jalisco-released)
- RealSense SDK's platform matrix must be read with release-specific caveats. Its macOS instructions currently say Viewer is unsupported and motion sensors are disabled; release notes call macOS compilable but not validated. [macOS instructions](https://github.com/realsenseai/librealsense/blob/master/doc/installation_osx.md), [release notes](https://github.com/realsenseai/librealsense/releases)
- DepthAI v3 docs target OAK/OAK4 hardware. Use camera generation and API generation together, not an arbitrary older tutorial. [Luxonis DepthAI docs](https://docs.luxonis.com/software-v3/depthai), [vendor repository](https://github.com/luxonis/depthai-core)
- SLAMTEC's `sllidar_ros2` lists specific RPLIDAR models and model-specific baud rates/launch files. This is an example of the correct driver path **only if** that vendor's LiDAR is supplied, not evidence that it will be. [SLAMTEC ROS 2 driver](https://github.com/Slamtec/sllidar_ros2)
- For an MLX90640 thermal module, Adafruit provides a Python driver. FLIR, USB thermal imagers and other arrays need their own paths. Do not download this as a universal thermal driver. [Adafruit MLX90640 driver](https://github.com/adafruit/Adafruit_CircuitPython_MLX90640)
- ESP-IDF is Espressif's fuller firmware framework and supports Mac hosts with its toolchain/build environment. It is useful when Arduino abstractions are insufficient, but duplicates setup for an introductory sensor demo. [ESP-IDF getting started](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html)
- MAVSDK-Python uses a matching `mavsdk_server`; certain Pi deployments may require explicitly running the server rather than relying on an embedded binary. PX4 documents a macOS development/simulation environment, but simulator availability alone does not validate a physical drone. [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python), [PX4 Mac environment](https://docs.px4.io/main/en/dev_setup/dev_env_mac)
- Ultralytics' repository is AGPL-3.0 with an alternative Enterprise license. The vendor explicitly discusses software **and models**. Do not infer that exporting weights to ONNX/HEF erases licensing obligations. It can be a useful P1 detector option after the team's intended distribution is understood, but it should not be silently embedded in a generically permissive starter. [Ultralytics repository](https://github.com/ultralytics/ultralytics), [vendor licensing page](https://www.ultralytics.com/license)
- OpenCV core is Apache-2.0, ONNX Runtime MIT, Picamera2 BSD-2-Clause, Hailo Apps MIT, and SLAM Toolbox LGPL-2.1 according to their upstream repositories. These labels apply to those repositories; downloaded weights, datasets, firmware and bundled dependencies require separate checks. [OpenCV](https://github.com/opencv/opencv), [ONNX Runtime](https://github.com/microsoft/onnxruntime), [Picamera2](https://github.com/raspberrypi/picamera2), [Hailo Apps](https://github.com/hailo-ai/hailo-apps), [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox)

### Inferences

- **Trust selection:** official owner, public docs, license and inspectable release history are meaningful signals; none establishes that a release is security-audited or works with the event image. Avoid anonymous binary bundles and random install scripts. The list does not claim all entries are fully open-source end-to-end: NVIDIA/Hailo firmware and compiler portions may remain vendor-controlled.
- Choose either Hailo's known-good accelerated example or an ONNX CPU baseline initially, rather than mixing every inference stack. Custom training is unlikely to be the highest-value pre-event task unless a required target cannot be handled by existing models.
- Battery/power, cold startup, reconnection and realistic lighting matter more to usefulness than benchmark TOPS. A box drawing around a person is a detection cue; it is not yet a reliable geographic location or verified survivor assessment.

### Gaps

- Hailo compiler host support and distribution access were not independently validated for the user's Mac. No native-Mac compilation promise is made; use precompiled models and ask organizers for a supported compiler environment if required.
- ROS docs denied automated access in this review. Official Open Robotics release announcement provides the Jazzy/Ubuntu support claim; a historical REP mirror was also observed as archived and is not used as a current global release recommendation.
- Some GitHub views omit release timestamps. No exact “latest” release number is asserted. A changing default branch is not a reproducibility pin.

## What is the practical readiness plan and evidence standard?

### Takeaway

A laptop that can replay one sample, compile one firmware example and display one timestamped event is more useful than a laptop containing many untested repositories. Preparation should end with an offline rehearsal and a written version record.

### Cited Findings

- Arduino IDE repository provides current download/support/security paths and states its maintenance process; its releases are preferable to building the editor from source for a hackathon. [Arduino upstream](https://github.com/arduino/arduino-ide)
- Picamera2, Hailo Apps and Espressif Arduino core expose release histories, providing a place to choose versions after matching the supplied hardware. This is evidence of maintained release channels, not proof that the newest release matches the organizers' image. [Picamera2 releases](https://github.com/raspberrypi/picamera2/releases), [Hailo Apps releases](https://github.com/hailo-ai/hailo-apps/releases), [Espressif releases](https://github.com/espressif/arduino-esp32/releases)
- pySerial's release page shows v3.5 and macOS/Apple Silicon-related fixes. Its relatively slow release cadence should be treated as mature but needing a local OS smoke test; it is not evidence of a newly validated build. [pySerial release history](https://github.com/pyserial/pyserial/releases)
- RealSense's release history explicitly records supported OS and JetPack combinations and known limitations. Those tables should be checked against the actual camera firmware and Linux kernel, not replaced with a claim that all platforms work equally well. [RealSense releases](https://github.com/realsenseai/librealsense/releases)

### Inferences

Recommended sequence, with timeboxes as planning estimates rather than measured installation times:

1. **First preparation session, about 60–90 minutes:** verify Git/Python/editor, install Arduino IDE, create virtual environment, test pySerial import and compile Blink for the likely board only after model confirmation. Keep the source PDF and module docs local.
2. **Second session, about 90–120 minutes:** choose one branch. Vision: decode local video and run a small model. Sensors: parse synthetic serial messages, timestamp and log them. Robotics: first prove existing robot vendor simulation rather than starting with autonomous navigation.
3. **Once organizers answer SKUs:** cache correct board packages, Pi image, firmware-specific docs, SDK packages, precompiled weights and licenses. Record version/tag/architecture/checksum. An ARM64 Pi wheel is not interchangeable with a Mac ARM64 wheel merely because both say ARM64.
4. **Offline rehearsal:** disable Internet while retaining local loopback/network if needed. Launch from a cold process, use only cached assets, emit an event and inspect it. Record startup time, dropped-data behavior and how stale observations appear. Distinguish simulation from physical testing in the demo.
5. **First hour on site:** inventory labels and power/interface ratings; boot organizer image; prove each peripheral independently; then connect two components. Save a working snapshot before installing more packages. Keep vision CPU/replay and manual-report fallbacks.

Minimal local checks to document after execution: `git --version`; `python3 --version`; environment creation; `python -m pip check`; `python -m serial.tools.list_ports`; IDE Blink compile; OpenCV local-file read if vision selected. Hardware checks are separate: actual serial upload/readback; camera capture; accelerator identification; driver sample; unplug/reconnect; offline event delivery. No physical proof should be claimed from successful imports.

### Gaps

The plan is not executed. Exact install commands for board packages and peripheral SDKs should remain conditional until SKUs arrive. Do not automatically reflash borrowed hardware or upgrade working organizer firmware during preparation.
