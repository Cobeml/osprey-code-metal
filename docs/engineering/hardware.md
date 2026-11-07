# Hardware inventory and integration gates

Updated November 7, 2026. Promised inventory, meeting reports and working integrations have different evidence levels.

| Component | Evidence available | Engineering gate |
| --- | --- | --- |
| Raspberry Pi 5, 16 GB | Organizer inventory promises per-team access | Record OS, architecture, supply, cooling and network |
| 26-TOPS accelerator | Organizer inventory; exact model unknown | Identify model and installed runtime before selecting compiled models |
| Arduino-compatible MCU, Grove shield and sensor kit | Organizer inventory | Record board/core, module IDs, voltage and interface |
| Visible or thermal camera | Shared equipment and team interest | Confirm checkout, model, resolution, frame rate, stream/API and calibration |
| Quadcopter | Meeting discussion; access pending staff confirmation | Confirm aircraft, staff operator, telemetry/API, payload and operating slot |
| LoRa or other radios | Shared inventory; proposed transport | Confirm paired devices, firmware, antennas, permitted settings and usable throughput |
| Robot dog or ground robot | Reported in discussion, unverified | Confirm access, SDK, power and a product reason before adding dependency |
| Laptop | Planned ship/operator role | Record host OS, runtime, ports, network and display |

The 26-TOPS rating resembles Hailo-8 but does not establish its identity. The named Hailo examples apply only after confirmation.

## Bring-up record

For every selected device, record model/serial alias, person responsible, connection diagram, power source and budget, software/firmware versions, working vendor example, acquisition command, output format and a sample capture.

Test the device independently before integrating. Record measured frame rate, end-to-end latency, disconnect behavior and recovery. Use reproducible mounting and reference points for localization measurements.

A camera can demonstrate image tracking while physically stationary. Physical pointing adds actuator feedback and control limits. Flight adds supported aircraft control, payload power/mass, link failsafes and staff operation.

Grove connectors do not establish electrical compatibility. Pi GPIO uses 3.3 V logic. Use suitable controllers and supplies for motors or pan-tilt actuators.

## Position and transport

Wi-Fi and LoRa can carry target observations. Accurate positioning from radio requires a suitable ranging/direction-finding method, hardware and calibration. The PRD must choose measured local geometry, valid GNSS/pose, or explicitly simulated positions.

Images require a separate budget from small telemetry messages. A 20 kB image every three seconds is approximately 53 kb/s before protocol overhead. Measure the selected link and decide whether thumbnails travel only on a higher-bandwidth channel or upon request.
