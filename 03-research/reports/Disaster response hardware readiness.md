# Disaster response hardware readiness

**The best preparation is a small, complete local system: sensor or report input → controller → Raspberry Pi → durable event store → responder display.** The guaranteed kit supports this direction; specialist cameras, radios and robots remain shared resources with unspecified models. Prepare Python, Arduino tooling and serial communication now, then select one hardware-specific extension. Details: [equipment](../../02-equipment/equipment-guide.md), [crash course](../../02-equipment/crash-course.md), [software](../../04-software/preparation-list.md).

## The baseline kit supports useful work immediately

The organizer's [inventory](../../02-equipment/source/Hackathon%20Hardware%20Details.pdf) provides every team access to a Pi 5 with 16 GB RAM and 26 TOPS accelerator, an Arduino-compatible controller/Grove shield, a 40-in-1 module kit, storage, power and development accessories. It does not identify the controller, module contents or accelerator model. A USB serial link lets the controller sample compatible modules while the Pi handles interpretation, storage and display. Grove reduces connector friction, but matching plugs do not establish matching voltage, protocol or driver. ([Grove system](https://wiki.seeedstudio.com/Grove_System/))

The practical first idea is an **offline incident board**, with a manual-report or labeled synthetic fallback when a particular sensor is unavailable. SQLite is suitable for local device/application data without a separate database server. That makes it a reasonable starting point for observations, a retry queue and review state. ([SQLite uses](https://sqlite.org/whentouse.html), [Mosquitto](https://mosquitto.org/))

## Radio links and local networks solve different problems

An outage-resistant design should state exactly which infrastructure it replaces. Local Wi-Fi or Ethernet can carry the dashboard and imagery without an Internet uplink. If the venue access point also disappears, the team needs its own supported local link; hotspot capability depends on the hardware/driver. ([NetworkManager](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html))

LoRa is a radio layer, not an application network. Meshtastic supplies an existing off-grid messaging path on supported devices, while LoRaWAN uses a different network architecture. Use compatible radios for compact alerts; keep images locally. Delivery acknowledgment is distinct from human review. ([Semtech LoRa](https://www.semtech.com/lora/what-is-lora), [Meshtastic hardware](https://meshtastic.org/docs/hardware/devices/), [radio settings](https://meshtastic.org/docs/overview/radio-settings/))

Offline mapping is a separate preparation task. MapLibre renders maps, while local data/assets must supply the style, glyphs, sprites and tiles. PMTiles offers an archive approach, but its local serving requirements and all remaining remote dependencies must be tested. ([PMTiles integration](https://docs.protomaps.com/pmtiles/maplibre))

## Model and device identity determine the AI stack

The 26 TOPS figure resembles Hailo-8 AI HAT+, but the PDF does not confirm that identity. If Hailo-8 is confirmed, use the matching precompiled vision example first. The reviewed Model Zoo directs Hailo-8/8L users to v2.x with Dataflow Compiler v3.x; its default branch serves newer accelerator families. The current Pi AI documentation also distinguishes mutually exclusive package families and names 64-bit Pi OS Trixie. ([AI HAT comparison](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html), [Model Zoo](https://github.com/hailo-ai/hailo_model_zoo), [Pi AI setup](https://www.raspberrypi.com/documentation/computers/ai.html))

For laptop preparation, OpenCV plus a small, appropriately licensed ONNX model is a useful replay/CPU path. For actual Pi CSI capture, Picamera2 belongs on the supported Pi camera stack; depth, thermal and LiDAR drivers must match the allocated model. RealSense's current macOS instructions carry significant Viewer/motion-sensor limitations, so a Mac install is not proof of a ready Linux camera path. ([OpenCV](https://github.com/opencv/opencv), [ONNX Runtime](https://github.com/microsoft/onnxruntime), [Picamera2](https://github.com/raspberrypi/picamera2), [RealSense macOS](https://github.com/realsenseai/librealsense/blob/master/doc/installation_osx.md))

Sensing evidence must remain distinct from localization. Thermal contrast cannot reveal people through walls; GNSS reports receiver position; UWB ranges to participating endpoints; inertial position estimates drift. Combining them requires known geometry, timing and uncertainty. ([FLIR](https://www.flir.com/en-gb/discover/home-outdoor/can-thermal-imaging-see-through-walls/), [GPS](https://www.gps.gov/gps-accuracy-0), [Qorvo UWB](https://www.qorvo.com/products/wireless-connectivity/ultra-wideband), [inertial navigation](https://rotations.berkeley.edu/strapdown-inertial-navigation/))

## Prepare a compatible set instead of every toolkit

**Python and basic Arduino C/C++ provide the broadest immediate coverage.** Add shell/SSH competence, then JavaScript/TypeScript if a custom browser UI requires it. Node-RED/FlowFuse is a credible alternative for rapid visual integration. ROS 2, navigation, drone stacks, GNU Radio and TAK become worthwhile when their specific integration is central and supported hardware or a real receiver is available. ROS Jazzy/Ubuntu 24.04 is a documented pairing; it does not make Pi OS or macOS equivalent installation targets. ([Node-RED](https://github.com/node-red/node-red), [FlowFuse Dashboard](https://github.com/FlowFuse/node-red-dashboard), [Open Robotics](https://www.openrobotics.org/blog/2024/5/ros-jazzy-jalisco-released))

Upstream ownership, licenses and support histories inform selection; they are not security audits. OpenCV's Apache-2.0 core, ONNX Runtime's MIT runtime and other permissive libraries do not license third-party weights, firmware, maps or datasets. Ultralytics explicitly offers AGPL-3.0 and Enterprise terms for its software/models; exporting a model does not remove that consideration. ([Ultralytics licensing](https://www.ultralytics.com/license))

Request exact SKUs/images and known-good examples, then cache compatible packages, firmware and models. The [preflight](../../04-software/preflight-checklist.md) defines proposed cold-start, persistence, duplicate, stale-data and reconnect checks. No installations or hardware tests were performed for this research, and no field performance is established. Choose one responder action from the [five ideas](../../01-ideas/idea-shortlist.md).

Checked 2026-10-29. Notes: [hardware](../research_notes/Disaster%20response%20hardware%20readiness/hardware.md), [software](../research_notes/Disaster%20response%20hardware%20readiness/software.md), [integration](../research_notes/Disaster%20response%20hardware%20readiness/integration.md).
