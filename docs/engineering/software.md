# Software and public repository shortlist

Research reviewed November 7, 2026. The accepted stack is a Python backend and browser-based coordinator display in one repository. Dependency versions and hardware adapters await bring-up. The following repositories are candidates with specific roles.

| Component | Candidate | Use and constraint |
| --- | --- | --- |
| Pi inference | [Hailo Pi examples](https://github.com/hailo-ai/hailo-rpi5-examples) | Run the supplied-image-compatible example first if the accelerator matches. Generic person detection has unmeasured swimmer performance. |
| Tracking | [Roboflow Trackers](https://github.com/roboflow/trackers) | Associate detections from the chosen model. Verify current API and pinned license. |
| Video annotations | [Supervision](https://github.com/roboflow/supervision) | MIT tools for processing and annotating detection results. |
| Tracking reference | [FoundationVision ByteTrack](https://github.com/FoundationVision/ByteTrack) | MIT original implementation. Benchmark GPU performance does not establish Pi speed. |
| Estimation | [DSTL Stone Soup](https://github.com/dstl/Stone-Soup) | MIT framework for tracking, state estimation and missing measurements. Start with a single relevant example. |
| Drift scenarios | [OpenDrift](https://github.com/OpenDrift/opendrift) | GPL-2.0 framework with Leeway SAR model. Dedicated environment and forcing data add work. Consider precomputing scenarios. |
| Conditional aircraft interface | [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) | Use only for a verified MAVLink-compatible aircraft. The listed FPV drones and Crazyflie do not establish MAVSDK compatibility. Crazyflie needs its native supported control stack. |
| Maritime benchmark | [SeaDronesSee](https://github.com/Ben93kie/SeaDronesSee) | RGB video, evaluation kits and model samples. Optional research/evaluation reference. Accepted demo inputs are live. |
| Detection evaluation | [MOBDrone_eval](https://github.com/ciampluca/MOBDrone_eval) | Notebook using saved predictions and dataset images. Code-license status needs confirmation. |

## Version and access findings

Current [Supervision documentation](https://supervision.roboflow.com/latest/how_to/track_objects/) states that sv.ByteTrack was removed in 0.31.0 and demonstrates ByteTrackTracker from the separate trackers package. Pin compatible dependencies instead of mixing old examples with latest packages.

The old [Hailo apps infrastructure](https://github.com/hailo-ai/hailo-apps-infra) URL redirects to hailo-apps. Match the installed accelerator runtime and examples.

The [PDMS MOB repository](https://github.com/DTU-IPL/pdms-man-overboard) currently contains only a README promising a later release. The [MAMMS dataset](https://zenodo.org/records/17979190) offers thermal imagery and a geolocation subset but requires an access agreement and download link.

## Accepted implementation baseline

One person uses Claude or Codex to implement and integrate the Python backend and browser display. Keep capture, perception, storage, drift and flight adapters independently testable. Start with one live camera through observation production, receiver and display. Select adapters after device checkout.

Store events locally using an implementation appropriate to the chosen stack. Keep perception, world-coordinate estimation and transmission independently testable. Pin selected libraries and model artifacts. Cache dependencies and required assets for the event demonstration.

Record upstream URL, commit/release, code license, model/data license, target platform, install command and smoke-test result for each adopted dependency. Source review has been performed; local installation and compatibility testing remain pending.

## Optional thermal integration

Visible-light input is sufficient for both demo nodes. If thermal hardware is selected, identify the exact device and use its supported driver or SDK and stream format. Verify frame decoding, timestamps, preprocessing and a detector suitable for that thermal imagery, then exercise tracking through the normal observation path. Confirm any accelerator model compatibility on the actual device. Enable the thermal option only after a live capture, detection and tracking check succeeds. Record software versions, model provenance and measured results. Thermal support remains pending hardware selection and testing.

## Ordered build sequence

The single implementation owner completes each runnable increment before broadening scope. Hardware checkout starts first because capture/control interfaces determine feasible behavior. No runtime package or version has yet been installed or verified.

| Step | Deliverable | Gate |
| --- | --- | --- |
| 1. Hardware checkout | Inventory chosen aircraft, radio, receiver/capture, camera proxy, accelerator and positioning accessories. Run vendor capture/control examples with flight operator | Save one live frame from each intended source and document actual flight mode. Record blockers and accepted pilot fallback |
| 2. Shared contracts and skeleton | Python service, browser shell, incident IDs, per-node identity, capture timestamps, location provenance and command acknowledgment | One live input reaches display. Pin dependencies and document exact run command |
| 3. Perception and incident lifecycle | Detection, initial confirmation, track association, retained screen grab/location, stop and End Incident | Exercise V-01 and basic V-11. Use explicit simulated location adapter if needed |
| 4. Two-node display | Second independent input, simultaneous streams, per-node state and geographic association | Exercise V-07 and V-09. Benchmark both feeds together |
| 5. Outage and history | Ground retention, isolated coordinator transport, local display snapshot aging, newest-first recovery and ordered history | Exercise V-02, V-03, V-05 and V-08 |
| 6. Drift scenario | Selected model, preloaded wind/current data, provenance, coordinate mapping, growing estimate and independent accelerated clock | Exercise V-04 and clock/quality boundaries in V-06 |
| 7. Flight integration | Confirm-to-follow, configured geometry, fixed-camera target framing, visual-loss behavior, override/failsafe and operator recovery | Exercise V-10 and complete V-11 with actual supported mode |
| 8. Rehearsal and evidence | Clean checkout, startup, full demonstration, measured results and limitations | Complete verification checklist and reconcile provisional targets |

Use small labeled synthetic messages for development and boundary tests. Keep acceptance video live. An optional thermal adapter enters only after its hardware/software gate passes and must use the same observation contract.

## Component choices to finalize during implementation

- Identify the accelerator before choosing its model compiler/runtime. Benchmark live two-stream throughput.
- Choose a browser-compatible live video transport after proving the drone capture path. Record latency and reconnect behavior.
- Use the aircraft manufacturer's supported control stack for the checked-out model. For Crazyflie, verify the native Python library and radio/positioning examples against the installed environment.
- Choose and pin a wind/current-driven drift model. OpenDrift/Leeway remains a candidate, subject to dependency readiness and appropriate environmental forcing data. Record object coefficients and uncertainty assumptions.
- Choose a durable local observation store and receiver ordering policy. Keep event persistence and current state updates consistent under retries.
- Define heartbeat cadence and coordinator-link timeout independently from observation cadence. The three-second observation cadence remains a proposal.
- Record the scenario-to-real-time mapping and reseeding policy. Simulated ocean locations are display/estimation inputs and must not drive physical flight navigation.
