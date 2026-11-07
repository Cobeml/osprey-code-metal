# Hardware inventory and integration gates

Updated November 7, 2026. Promised inventory, meeting reports and working integrations have different evidence levels.

| Component | Evidence available | Engineering gate |
| --- | --- | --- |
| Raspberry Pi 5, 16 GB | Organizer inventory promises per-team access | Record OS, architecture, supply, cooling and network |
| 26-TOPS accelerator | Organizer inventory; exact model unknown | Identify model and installed runtime before selecting compiled models |
| Arduino-compatible MCU, Grove shield and sensor kit | Organizer inventory | Record board/core, module IDs, voltage and interface |
| Visible or thermal camera | Shared equipment and team interest | Confirm checkout, model, resolution, frame rate, stream/API and calibration |
| Quadcopter | Flight access and six available models confirmed by user. Selected unit/revision pending | Confirm aircraft, staff operator, telemetry/API, payload and operating slot |
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

Wi-Fi and LoRa can carry target observations. Accurate positioning from radio requires a suitable ranging/direction-finding method, hardware and calibration. The PRD accepts real person geolocation where available and clearly labeled simulated person coordinates otherwise.

Images require a separate budget from small telemetry messages. A 20 kB image every three seconds is approximately 53 kb/s before protocol overhead. Measure the selected link and decide whether thumbnails travel only on a higher-bandwidth channel or upon request.

## Available aircraft review — November 7, 2026

User reports access to EMAX Tinyhawk II, BETAFPV Aquila16, NewBeeDrone VRDrone, EMAX Tinyhawk Lite 75 mm, BETAFPV Cetus X 2S and Crazyflie 2.1+. Exact revisions and accessories require physical inventory. Manufacturer documentation review is not a hardware test.

| Aircraft | Documented capabilities and integration implication |
| --- | --- |
| Crazyflie 2.1+ | Programmable flight using computer scripts and Crazyradio. Autonomous flight requires positioning sensors or an external positioning system. Camera is an additional integration, such as AI deck 1.1. Strongest candidate for custom autonomy, conditional on available accessories and successful integration. |
| Aquila16 | Assisted hover and analog FPV. Camera angle adjusted mechanically. No built-in person-following or motorized camera-pointing feature identified in reviewed documentation. Pilot fallback candidate. |
| Cetus X 2S | Cetus and Betaflight controller variants differ. Manufacturer lists hold support for Cetus FC and adjustable camera angle. No built-in person-following or motorized camera-pointing feature identified. Verify exact variant. |
| Tinyhawk II | FPV racing platform with RunCam Nano 2 and video transmitter. No built-in person-following or motorized camera-pointing feature identified. |
| Tinyhawk Lite 75 mm | Manufacturer describes Betaflight, RunCam Nano 3 and analog video. No built-in person-following or motorized camera-pointing feature identified. |
| VRDrone | Manufacturer currently lists V2.5 with analog video. User inventory revision is unspecified. Autonomous tracking and camera actuation remain unverified. |

For analog FPV, verify a compatible receiver and live computer capture path before promising display integration. For Crazyflie, inventory Crazyradio, a positioning solution such as Flow deck or external positioning, and a camera solution such as AI deck. AI deck 1.1 has a 320 by 320 monochrome camera and Wi-Fi. Custom person tracking and following still require implementation. The AI bundle page flags GAP SDK autotiler availability problems and describes DORY as an alternative. Check installed tooling before choosing onboard inference.

No reviewed stock configuration establishes the complete required person-following and camera-pointing behavior. PRD D-40 accepts fixed-camera following through aircraft movement, with a defined central image region and labeled pilot assistance where needed. Pilot fallback is already authorized if autonomy is unsupported.

Sources reviewed

- https://www.bitcraze.io/products/crazyflie-2-1-plus/
- https://github.com/bitcraze/bitcraze-website/blob/master/src/support/f-a-q.md
- https://www.bitcraze.io/products/ai-deck/
- https://store.bitcraze.io/products/the-ai-bundle
- https://betafpv.com/products/aquila16-brushless-quadcopter
- https://betafpv.com/products/cetus-x-brushless-quadcopter
- https://shop.emax-usa.com/collections/hot-products/products/emax-tinyhawk-2-indoor-fpv-racing-drone-bnf
- https://shop.emax-usa.com/pages/getstarted
- https://newbeedrone.com/collections/newbeedrone-vrdrone/products/newbeedrone-vrdrone-rtf-bundle-kit-v2-5
## Equipment allocation proposal

Reviewed the organizer equipment extraction and the user-supplied aircraft list. The per-team kit is promised. Shared-library entries identify categories only, with exact models, quantities and checkout unverified. Allocations below are engineering proposals.

| Equipment | Proposed role | Integration gate |
| --- | --- | --- |
| Pi 5 16 GB and 26-TOPS accelerator | Ground-based live detection/tracking for two logical sensor nodes, observation retention and transport | Identify accelerator, pin its runtime/model, benchmark both feeds together |
| Laptop and portable monitor | Coordinator display, map, history and drift calculation | Verify simultaneous video decoding and display latency |
| Standard/wide-angle camera or phone | Live second-drone proxy | Verify stream API and timestamps |
| Pan-tilt mechanism, servos, MCU/Grove shield | Optional physical target pointing for the ground camera proxy | Confirm mounting, motor power, voltage levels and motion limits |
| Crazyflie and compatible radio/positioning/camera accessories | Conditional autonomous flight and fixed-camera following | Check actual accessories, flight control example and target-following loop |
| Listed FPV drones | Pilot-assisted aerial video fallback | Verify receiver and live USB/computer capture hardware, absent as a specific guaranteed inventory item |
| Wi-Fi adapters | Live feeds and observation transport | Measure concurrent throughput, loss and recovery |
| Depth camera | Optional metric position/range for the proxy and independent test reference | Verify device range, calibration, coordinate frame and SDK |
| UWB/localization modules | Optional local positioning | Require compatible tags, anchors, geometry and software. Generic UWB inventory does not establish Crazyflie Loco compatibility |
| GNSS and IMU | Optional real aircraft pose inputs | Aircraft pose alone cannot establish person location. Indoor GNSS suitability and synchronization need validation |
| Thermal camera | Optional alternate sensor | Apply thermal software integration gate in software.md |
| LoRa | Optional low-rate status channel | Measure payload/rate. Continuous video needs a separate suitable link |
| Grove button/LED if included | Optional physical MOB declaration/status indication | Verify kit contents and reuse the same incident API as the display |
| Power supplies, USB hubs, batteries and test equipment | Stable operation, bring-up and flight turnaround | Validate power and connector compatibility |

Keep Pi/Jetson-class compute and general-purpose pan-tilt hardware on the ground in the initial design. Crazyflie 2.1+ lists 15 g maximum recommended payload. Ground processing means the video link to that processor is required for perception. To demonstrate continued tracking during coordinator outage, interrupt the downstream processor-to-display link separately. Loss of the camera-to-processor link cannot be presented as continued onboard tracking. This adaptation is accepted under PRD D-41.

Optional Jetson hardware is a compute fallback if the supplied accelerator path fails. Radar, environmental sensors and ground robots currently have no necessary role in the accepted demo. Local environmental sensors do not supply the ocean-current dataset used for drift prediction.

References for physical integration constraints

- https://www.bitcraze.io/products/crazyflie-2-1-plus/
- https://www.bitcraze.io/loco-pos-system/
- https://www.bitcraze.io/products/loco-positioning-deck/