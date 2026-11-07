# Code Metal hackathon handover

Prepared **November 7, 2026**, America/New_York. This file is a standalone project briefing for the owner, a teammate, or a new coding assistant. It contains enough context to resume without this chat; relative links provide the detailed evidence when the project folder is available.

**Current outcome:** research, equipment explanations, a crash course, software preparation guidance, project ideas, and PDFs are complete. A generic code scaffold exists. No application, firmware integration, selected product, or measured hardware demonstration exists in the inspected project.

**Best next step:** confirm the actual equipment and choose one responder decision to support. The leading proposal is an offline incident board, with one sensor or manual report flowing into local storage and a responder display. This remains a recommendation, not a selected implementation.

## 1. Mission and requested work

The supplied prompt is:

> The mission: help locate people, detect hazards, and get critical information to responders when infrastructure goes down. Start thinking about what you could build—and what could make a difference when every second counts.

The owner requested:

1. Preserve the prompt and attached equipment inventory.
2. Explain what each equipment type does, how it can be used, and how it could connect to other hardware.
3. Provide a beginner crash course on the technologies and capabilities.
4. Research trusted, preferably open-source repositories, software suites and languages; rank what to prepare and explain why.
5. Organize the project into numbered ideas, equipment, research and software folders, with a README and index.
6. Set up a generic Git repository for later coding.
7. Export the main guides as PDFs, then produce this portable Markdown handover.

“Next week” was stated on October 29. It is historical wording, not a current event date. The exact event date, venue, team size, judging criteria and supplied device model numbers are still not recorded here. Mac preparation has been an assumption; the laptop being brought is unconfirmed.

## 2. Location and repository state

The current verified project root is:

```text
/Users/dexter/Projects/code-metal-hackathon
```

The former path `/Users/dexter/OS/code metal hackathon` no longer exists. Old chat working-directory bindings and earlier links may still point there. Set the working directory explicitly to the current root before running commands.

### Live local verification on November 7

| Item | Verified state |
|---|---|
| Git boundary | Whole project root; starter is a subtree |
| Branch | `main` |
| HEAD | `f2e856b57583151947a2b4f97826969930f72fa3` |
| HEAD subject | `Reconcile starter documentation with private workspace remote` |
| Previous commit | `5b6ca27b505b81aa2042b9c6e557b1618fcbd936` — `Complete standalone repository migration` |
| Both commit dates | November 3, 2026 |
| Origin URL | `https://github.com/colt11044/code-metal-hackathon.git` |
| Local tracking display | `main...origin/main`, without ahead/behind counts at inspection |
| Nested starter `.git` | Absent; do not initialize another repository there |
| Staging area | Empty at inspection |
| Existing uncommitted work | Modified `INDEX.md` and seven untracked PDF exports |
| This handover change | Adds `HANDOVER.md` and updates index links; no staging, commit or push performed |

The repository is documented as private. Current GitHub visibility, remote availability and server-side HEAD were not queried during this handover. A locally configured origin and cached tracking ref do not establish that every current local file is on GitHub.

**Documentation drift:** older sections of the index, preflight, PDFs and research still describe an unborn repository without a remote or initial commit. Those statements describe the earlier setup. Use the verified state above for resumption. The index is being updated with this handover; older PDFs remain dated exports.

A root `.gitignore` is now present as well as the starter ignore file. It excludes common secrets, dependency environments, generated data and machine-specific assistant configuration. Ignore rules are a convenience, not proof that a file is safe to publish.

## 3. What has been delivered

The [project index](INDEX.md) is the navigation entry point. The editable Markdown files are the working sources; PDFs are reading copies.

| Deliverable | Markdown or source | PDF |
|---|---|---|
| Overview and reading order | [README](README.md) | — |
| Mission and confirmed context | [Project brief](01-ideas/brief.md) | — |
| Five possible projects | [Idea shortlist](01-ideas/idea-shortlist.md) | [2 pages](01-ideas/idea-shortlist.pdf) |
| Every listed hardware type | [Equipment guide](02-equipment/equipment-guide.md) | [11 pages](02-equipment/equipment-guide.pdf) |
| Three-hour learning sequence | [Crash course](02-equipment/crash-course.md) | [6 pages](02-equipment/crash-course.pdf) |
| Source-backed synthesis | [Research report](03-research/reports/Disaster%20response%20hardware%20readiness.md) | [3 pages](03-research/reports/Disaster%20response%20hardware%20readiness.pdf) |
| Ranked tools and languages | [Preparation list](04-software/preparation-list.md) | [7 pages](04-software/preparation-list.pdf) |
| Preparation and arrival checks | [Preflight checklist](04-software/preflight-checklist.md) | [3 pages](04-software/preflight-checklist.pdf) |
| Combined six-guide reading pack | — | [33 pages with bookmarks](Hackathon%20preparation%20pack.pdf) |
| Original organizer inventory | [Original PDF](02-equipment/source/Hackathon%20Hardware%20Details.pdf), [extracted text](02-equipment/source/equipment-extracted.txt) | 2 pages |

Supporting research notes preserve the source details:

- [Hardware capabilities and interfaces](03-research/research_notes/Disaster%20response%20hardware%20readiness/hardware.md)
- [Software, compatibility and licensing](03-research/research_notes/Disaster%20response%20hardware%20readiness/software.md)
- [Networking, integration and project directions](03-research/research_notes/Disaster%20response%20hardware%20readiness/integration.md)

Research was checked on **October 29**. PDFs were created on **November 6**. This handover verifies local artifacts and repository state on **November 7**, but does not refresh upstream technical claims, releases or licenses. Recheck the relevant official documentation when selecting actual hardware and versions.

The preserved organizer PDF has SHA-256:

```text
069bdb5540c854e385475073ed4a2a8731a6c59184013f77a397450b764aee76
```

This hash was recomputed and matched during the handover. The extracted text is a convenience copy; the PDF is the original source.

## 4. Equipment facts and unknowns

### Baseline access promised to every team

- Raspberry Pi 5, 16 GB RAM, with a 26 TOPS AI accelerator, storage and power supply.
- Arduino-compatible microcontroller with Grove expansion shield.
- Grove 40-in-1 sensor and actuator kit.
- Development accessories for circuits, sensors and hardware connections.

The PDF does not identify the accelerator, controller, shield or all 40 modules. The 26 TOPS rating is consistent with a Hailo-8 AI HAT+, but that is an inference. A camera is not explicitly guaranteed with the baseline kit.

### Shared checkout library

| Category | Listed equipment and useful role |
|---|---|
| Compute | Pi Zero, ESP32, Arduino, Jetson and other boards; additional sensor nodes or heavier processing |
| Cameras | Standard, wide-angle, low-light/NoIR, AI-enabled and depth; imagery, inference or range |
| Thermal and infrared | Thermal cameras and IR sensors; thermal contrast, proximity or model-specific measurements |
| Distance | 2D/3D LiDAR, time-of-flight and ultrasonic; obstacle and geometry measurements |
| Localization | GNSS, positioning modules, IMUs, accelerometers, gyroscopes and magnetometers; receiver position and motion |
| Communications | SDR, Wi-Fi, Bluetooth, LoRa, UWB and other radios; links or ranging depending on device |
| Motion | mmWave, Doppler radar and PIR; model-dependent movement or presence sensing |
| Environment | Temperature, humidity, pressure, gas, air quality, light and other sensors |
| Audio | Microphones, speakers, acoustic sensors and audio processing modules |
| Robotics | Wheeled, tracked and legged robots, arms and development kits; mobile or aimed sensing |
| Aircraft | Programmable microdrones, FPV drones and development platforms; APIs and permissions vary |
| Actuators | DC motors, servos, controllers and pan-tilt mechanisms |
| Prototyping | Breadboards, wires, connectors, resistors, LEDs, switches and components |
| Debugging | Multimeters, oscilloscopes, logic analyzers, serial adapters and bench supplies |
| Assembly and accessories | Soldering/crimping tools, insulation, hand tools, monitors, USB hubs, batteries, power supplies, cables and adapters |

Availability, quantities, checkout rules, working drivers and exact models remain unconfirmed. Design the first demonstration around baseline access; make a shared item essential only after securing it.

## 5. Proposed architecture and technical lessons

The simplest proposed implementation is:

```text
Grove sensor or manual input
          |
Arduino firmware -- USB serial --> Pi / Python adapter
                                      |
                              local SQLite store
                                      |
                              local responder UI
                                      |
                          browser via local network

Optional camera --> local inference --> candidate detection + evidence
Optional paired LoRa radios ---------> compact remote alerts
```

The microcontroller samples sensors and handles simple outputs. The Pi runs Linux applications, stores observations and serves the interface. A network moves information; it does not replace durable storage. An observation, an interpreted alert and a responder acknowledgment are separate records or states.

Key limits carried forward from the research:

- Pi GPIO is 3.3 V logic; direct 5 V signals can damage it. Grove connectors do not guarantee voltage or protocol compatibility. Analog inputs need an ADC somewhere in the path.
- Motors require suitable controllers and power. GPIO is a control signal, not a motor supply.
- AI accelerators run compatible models and operators. TOPS is not a measured frame rate or a promise of arbitrary model support.
- NoIR captures near-infrared light; it is not thermal imaging. Thermal cameras do not see through walls.
- GNSS locates its receiver. UWB requires participating endpoints and suitable geometry. IMU position estimates drift. A detected person's map coordinate requires additional geometry and uncertainty handling.
- Wi-Fi can operate locally without Internet. Losing Internet and losing the local access point are different failure cases.
- LoRa is a radio layer; LoRaWAN and Meshtastic add different network behavior. A generic ESP32 is not automatically a LoRa device. Use small alerts over a low-rate link; keep imagery local or on Wi-Fi.
- Offline maps need local styles, fonts/glyphs, sprites, scripts and geographic data. Installing a renderer alone is insufficient.
- Sensor readings and AI predictions are not confirmed rescue findings or certified hazard measurements. Preserve units, provenance, age and uncertainty.

These lessons are explained and sourced in the [equipment guide](02-equipment/equipment-guide.md) and [crash course](02-equipment/crash-course.md). No range, runtime, detection accuracy or calibrated hazard threshold has been measured for this project.

## 6. Software and language priorities

This is a summary of the existing preparation research, not an installed-software inventory or a freshly tested version lock.

| Priority | Tools | Reason and dependency |
|---|---|---|
| P0 | Git, familiar editor, Python, virtual environment, shell/SSH | Broadest usefulness for versioning, adapters, local services and device access |
| P0 | Arduino IDE, correct board core and module libraries | Firmware for the promised Arduino-compatible controller; core/libraries depend on exact models |
| P0 | pySerial, Python SQLite support | Straightforward controller-to-Pi data path and durable local records |
| P0 | Pi Imager, approved recovery image and setup docs | Recovery preparation; preserve a supplied working image |
| P1 vision | OpenCV, Picamera2 where applicable, ONNX Runtime or matching accelerator examples | Capture/replay first, then compatible inference; Pi camera drivers belong on their supported target |
| P1 connectivity | Meshtastic on supported paired radios; Mosquitto/Paho if multiple event producers need a broker | Radio hardware and protocol must match; MQTT is optional for the simplest local service |
| P1 interface | A small browser UI; Node-RED/FlowFuse as an alternative | Choose one route rather than building duplicate UI stacks |
| P1 mapping | MapLibre plus locally served map assets/PMTiles | Only when a map materially improves the responder workflow |
| P1 device-specific | ESP32 core, depth/thermal/LiDAR SDKs | Select after actual board and sensor identification |
| P2 | ROS 2/Nav2/SLAM, JetPack, drone SDKs, GNU Radio, GPSD, TAK | Use when the chosen project and available platform specifically require them |

Learn Python first, enough Arduino C/C++ for sampling and serialization, then shell/SSH. JavaScript/TypeScript is useful for a custom interface. SQL helps inspect local records. Rust, CUDA and advanced robotics are not general prerequisites.

Important dated compatibility findings to recheck before installation:

- Hailo-8/8L and newer Hailo generations use different model/compiler/runtime paths. The October research pointed Hailo-8/8L toward Model Zoo v2.x rather than the default newer-generation branch.
- Pi OS, Ubuntu ROS targets and macOS are not interchangeable installation environments. Apple ARM and Linux ARM packages are different builds.
- Jetson images and JetPack versions must match the particular device.
- RealSense and other camera support vary by OS, hardware and SDK generation.
- Runtime, model weights, firmware, datasets and map data can have separate licenses. Choose the actual artifacts before concluding their terms fit the project.

Official repositories, documentation links and the detailed priority rationale are in the [software preparation list](04-software/preparation-list.md). Cache the selected packages, board cores, firmware, models, documentation and example inputs before relying on an offline demo.

## 7. Ideas considered, with no selection yet

| Idea | Value | Main dependency or risk | Fallback |
|---|---|---|---|
| Offline incident board | One local view of observations, freshness and acknowledgment | Durable storage and recovery behavior | Manual reports or labeled synthetic inputs |
| Hazard breadcrumb nodes | Conditions relayed from placed nodes | Suitable sensors, calibration limits and optional paired radios | USB/local Wi-Fi delivery |
| Human presence review station | Candidate sightings with reviewable evidence | Camera, matching inference stack and false detections | Consented recorded footage labeled replay |
| Team location and last contact | Position and contact age for consenting teammates | GNSS/radio availability; UWB needs its own infrastructure | Manually placed markers with provenance |
| Teleoperated inspection scout | Human-directed remote inspection | Working robot SDK, power, control and lost-link stop | Handheld or stationary sensor station |

The incident board is the leading preparation recommendation because it can demonstrate useful information handling with the baseline kit. The owner has not selected it. Details and proposed demo tests are in the [idea shortlist](01-ideas/idea-shortlist.md).

## 8. Code scaffold and data contract

The code area is `04-software/starter/` within the root repository:

```text
04-software/starter/
  README.md
  .gitignore
  docs/architecture.md
  examples/event.example.json
  src/.gitkeep
  firmware/.gitkeep
  tests/.gitkeep
  scripts/.gitkeep
```

The four implementation directories contain placeholders only. There is no application entry point, dependency lockfile, firmware, formal schema, build command, test suite or deployment in this scaffold. The architecture file describes proposed boundaries: device adapter, observation record, local store, transport adapter and responder view.

The existing example is valid JSON and explicitly simulated:

```json
{
  "schema_version": "0.1-draft",
  "id": "simulated-temperature-observation-001",
  "observed_at": "2026-10-29T12:00:00Z",
  "source": {
    "device_id": "simulated-sensor-001",
    "adapter": "example-fixture"
  },
  "type": "temperature_observation",
  "measurement": {"value": 24.0, "unit": "degC"},
  "location": {
    "coordinates": null,
    "coordinate_frame": null,
    "uncertainty_m": null
  },
  "simulated": true
}
```

This is an illustrative contract, not a validated schema. Unknown coordinates and uncertainty are null; they must not become zero. No confidence value is invented for an ordinary temperature reading. Before implementation, settle timestamp quality, receipt time, source sequence, deduplication, location provenance, acknowledgment states and data retention. See [architecture notes](04-software/starter/docs/architecture.md).

## 9. Verification and remaining uncertainty

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Original PDF hash matches | Saved inventory integrity | Supplied models or actual availability |
| Markdown guides, notes and PDFs exist | Research and reading deliverables are available locally | Current upstream compatibility |
| PDFs reopen with expected page counts | Readable PDF structure; combined pack has 33 pages | Technical accuracy beyond the dated sources |
| November 6 rendering review | Tables, diagram, code and pages were visually inspected | Hardware behavior |
| Example parses and `simulated` is true | Sample record syntax and labeling | Application/schema validation |
| Git root, HEAD, branch and origin inspected | Current local repository arrangement | Fresh remote synchronization or visibility |
| Empty implementation directories | Scaffold remains generic | A runnable end-to-end product |

No hardware tests, project package installation, emergency-use reliability, or field-performance validation are part of the recorded project work. The host's globally installed tools were not comprehensively audited.

On this host, the default system Git previously reported an unaccepted Xcode license. The bundled Git executable worked for this handover's read-only inspection. On another machine use its own functioning Git installation; do not copy machine-specific runtime paths as a project dependency or automatically accept license agreements.

## 10. Open decisions and organizer questions

Resolve these before committing to a hardware-heavy implementation:

1. What exact event date, demo duration, judging criteria and sponsor requirements apply?
2. Who is on the team, what skills are available, and what laptop OS/CPU will be used?
3. Which responder decision or action should the demo improve?
4. What are the exact controller, Grove shield and module IDs, signal voltages, board cores and working examples?
5. What accelerator and Pi OS/runtime image are supplied? Are cooling, compiled models or a camera included?
6. Which shared devices can be reserved, and which have known-good SDK examples?
7. Does “infrastructure down” mean no Internet, no cellular, no venue Wi-Fi, or all of these? Can the team operate its own access point?
8. For LoRa/UWB, what device counts, firmware, antennas, region settings and anchor/tag configurations are supplied?
9. What power, batteries, cables, robot/drone areas and operating procedures are available?
10. Is integration with a real responder system required, or is a local demonstration sufficient?

The questions are saved; no organizer outreach has been performed in this work. Unknowns are not approvals or confirmed capabilities.

## 11. Suggested implementation sequence

These are proposed next steps, not completed work or a final stack decision.

### Milestone 1 — Select and constrain

Confirm one responder problem, one primary input and one display/delivery path. Record exact device models and software image versions. Choose a baseline fallback. Agree on what the demo will prove and who owns each part.

**Exit condition:** a one-paragraph scope and a device/dependency list without unidentified critical components.

### Milestone 2 — Working local path

Implement a labeled replay or manual event producer, local persistence and a minimal display showing source, time, type, value/unit and review state. If selected, Python and SQLite are sufficient starting choices; framework selection remains open.

**Exit condition:** ten unique demo events survive a process restart, and replaying an existing ID does not create a duplicate incident.

### Milestone 3 — One real input

Run the device vendor's independent example. Establish serial communication and parse valid readings. Preserve units, timestamps, provenance and error states. Only then connect it to the application.

**Exit condition:** a physical input reaches the display; unplugging it produces stale/unknown status rather than an apparently healthy old reading.

### Milestone 4 — One optional extension

Choose a camera, paired radio, map or robot branch according to the selected idea. Use the supplied working example first. Keep a replay/manual fallback. Record actual versions and measured behavior.

**Exit condition:** the extension adds a clear responder benefit while the baseline path remains demonstrable.

### Milestone 5 — Rehearse the actual outage

Cold-start with Internet removed; test local-network loss separately if in scope. Restart services, interrupt the transport, replay duplicates and inspect stale records. Distinguish transport receipt from human acknowledgment. For mobility, prove lost-command stop behavior.

**Exit condition:** a documented demonstration showing preserved observations, honest freshness, no accidental duplicates and recoverable communication. Mark every result as synthetic, replay or physical hardware evidence.

The [preflight](04-software/preflight-checklist.md) provides the before-arrival checklist and a proposed first-hour schedule. No timing in it is a measured setup guarantee.

## 12. Moving this handover to another machine

**For briefing only:** save this file as `HANDOVER.md` anywhere. The mission, status, architecture, software priorities, open questions and next steps above remain understandable without other files. Relative links will only work if the associated project files are also present.

**For full continuity:** copy the project folder, preserving its numbered directories, Markdown, source PDF, exported PDFs and starter subtree. If preserving Git history, include `.git`. Obtain any private-repository access through the receiving machine's normal authentication. Machine-specific assistant configuration and credentials should be configured separately, not treated as portable project content.

A Git clone is another way to obtain committed material, if authorized and accessible:

```sh
# Optional on the receiving machine; choose a destination that does not exist.
git clone https://github.com/colt11044/code-metal-hackathon.git
cd code-metal-hackathon
```

**A clone alone may omit this handover, the latest index and all seven PDF exports.** They were not committed or pushed by this handover work. Copy those files separately or review and commit the intended files before relying on remote transfer. No remote sync was performed here.

After copying or cloning, run read-only checks from the receiving project root:

```sh
# Replace the example path with the actual local folder.
cd '/path/to/code-metal-hackathon'
git rev-parse --show-toplevel
git status --short
git branch --show-current
git log -1 --oneline
git remote -v
python3 -m json.tool 04-software/starter/examples/event.example.json
```

A copied folder without `.git` can still be used for reading; its Git commands will fail until a deliberate repository setup is made. No application run command exists yet. Use the local Python/tool versions you intentionally select for the implementation; this project does not bundle a reproducible execution environment.

Source PDF integrity check using standard Python:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
path = Path('02-equipment/source/Hackathon Hardware Details.pdf')
print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

Compare the result with the hash in section 3. Confirm the linked PDFs open and the original sample remains labeled simulated. The PDF export script was temporary tooling, not a committed project build system; rebuilding PDFs is a separate formatting task.

## 13. Ready-to-use continuation prompt

> Read HANDOVER.md and inspect the current project files and Git state. This project has completed research and a generic scaffold, but no selected application or hardware integration. First resolve the actual equipment and the responder workflow we want to demonstrate. Use the saved equipment guide, software priorities and original inventory to avoid assuming device models or shared-hardware availability. Propose the smallest end-to-end demonstration and its acceptance criteria, then proceed according to my current build request. Keep physical tests, replay and simulation clearly labeled. Record selected versions, setup/run commands, results and unresolved issues so the next session can continue.

## 14. Maintenance notes

Update this handover when the team chooses a project, identifies devices, implements a milestone or verifies a deployment. Add the date and evidence for each change. Keep product decisions, proposed defaults and observed results distinct. Recheck Git state before reporting synchronization. Regenerate PDF reading copies after substantive source changes if they are needed for the next handoff.

This file contains project context only. It does not transfer credentials, grant external-action permission, install software, select a license or establish emergency readiness.
