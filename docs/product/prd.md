# Product requirements — open-ocean man-overboard demo

Consolidated November 7, 2026 after the product interview. Core scope is accepted. Implementation, hardware integration and measured results are pending. Hardware gates and provisional targets below remain explicit implementation inputs.

## Outcome and operator

Help the search-and-rescue coordinator on one responding ship maintain a useful picture of one person overboard. The coordinator directs the ship. The demo evaluates the display and system behavior. A spoken direction from the coordinator is outside its acceptance criteria.

The venue demonstration uses live detection of a person on land. Ocean coordinates may be simulated when real person geolocation is unavailable, with clear labels. A concurrent ocean drift simulation illustrates the search area using preloaded wind and current data.

## Accepted scope

- Two logical sensor nodes independently detect and track one person. One node uses an airborne drone. The other uses a live phone or camera as a proxy for another drone.
- Visible-light cameras satisfy the baseline. Thermal is optional after device-specific capture, preprocessing and detection have been integrated and tested.
- Both live feeds appear simultaneously when available. Each node retains its last valid screen grab, person location, capture time, age and loss state. Retained evidence remains visible through visual loss or unavailable video.
- A manual MOB declaration starts candidate detection. Initial coordinator confirmation selects the person and starts tracking and following.
- Aircraft following keeps the person in a defined central region of its fixed-camera image. Use autonomy where supported and clearly label pilot assistance otherwise. The flight operator sets separation and altitude for the venue and aircraft. Explain that real-world settings vary.
- Process video on the ground. The coordinator-outage test interrupts only processor-to-display communication. Ground processing and retention continue. Loss of drone-to-processor video is visual-input loss.
- Internet access is available. Python backend and browser display share this repository. One person uses Claude or Codex for implementation and integration. Hardware adapters are selected after checkout.
- Video replay is excluded from the accepted demonstration. Simulated coordinates and the accelerated drift scenario accompany live detections.

## Mission flow

1. Create an incident with MOB. Start automatic candidate detection on both live inputs.
2. Coordinator confirms the initial person. Store that accepted sighting and start tracking and following through the supported aircraft adapter or labeled pilot fallback.
3. Update the retained screen grab and person location automatically while tracking. Associate the second node using the geographic rule below.
4. Show each node independently. A healthy feed can continue contributing when the other node loses contact or communication.
5. During a five-second coordinator-link outage, retain observations at the ground processor. The display keeps its last received evidence and advances its age.
6. Restore current observations and live video first, then transfer timestamped history. Older observations cannot replace newer sightings.
7. Hide the person from both cameras for the separate visual-loss demonstration. After both accepted sightings become stale, show the concurrent growing drift estimate.
8. Reacquire according to the rules below. Stop or override remains available. End Incident stops tracking and following, preserves history and hands aircraft recovery to the flight operator.

## Association and reacquisition

| Situation | Required behavior |
| --- | --- |
| Initial target | Coordinator confirmation required |
| Same person remains tracked | Update both screen grab and location automatically |
| Reacquisition after visual loss | Measure horizontal distance from that person's last observed location immediately before visual loss |
| Reacquisition at distance <= 50 m | Resume updates and following automatically, including exactly 50 m |
| Reacquisition at distance > 50 m | Show candidate and retain the prior accepted sighting until coordinator confirmation |
| Missing or unreliable candidate/reference location | Require confirmation and retain prior accepted evidence |
| Second node first association | Automatically associate within 50 m inclusive of the most recent accepted person location. Use the same confirmation fallback outside the radius or with unreliable coordinates |
| Incorrect automatic association | Operator can stop or override following and divert the aircraft |

The 50 m value is a provisional demo setting. Compare locations only in a common coordinate frame with known units and provenance. The exact reliability criterion and handling of multiple simultaneous feasible candidates remain engineering decisions to document before implementation. Simulated coordinates may exercise these rules but must retain their provenance.

## Loss states and flight behavior

| Condition | Display and processing | Aircraft |
| --- | --- | --- |
| Person observed | Live video and fresh accepted evidence | Follow with configured geometry |
| Person hidden, input and coordinator links healthy | Visual contact lost, last accepted sighting and advancing age | Hold position while searching for reacquisition, subject to hardware capability |
| Drone video input unavailable | Visual-input loss, retained evidence and age | Apply visual-loss behavior or operator fallback |
| Processor-to-display connection unavailable | Coordinator link lost, current remote visual state unknown, last received sighting and advancing age | Continue following while processing, control path and pilot control link remain healthy |
| Pilot control link lost | Show status when it is available | Yield to configured aircraft failsafe |
| End Incident | Preserve history, stop mission tracking | Stop following and hand recovery to flight operator |

Fixed-camera search while holding position needs aircraft-specific verification. A search maneuver, hold tolerance and override transition must be documented with the flight operator. The ground camera proxy does not require an aircraft control loop.

## Drift simulation and clocks

When neither node has a fresh accepted sighting, display a growing search area clearly labeled as an estimate. Keep both last observed locations visible. Derive the estimate from the latest accepted observations and preloaded wind and ocean-current data. Display environmental data source, geographic coverage/location and time.

Use an explicit drift model with stated motion and uncertainty assumptions. Model and dataset selection are pending. An arbitrary expanding shape does not establish a drift-model result. A calibrated probability claim requires supporting evaluation.

The drift simulation may accelerate time. Show simulated elapsed time and speed. Video, capture age, freshness, link-outage duration and recovery timing use real elapsed time. Anchor scenario time to the accepted observation used to initialize the estimate. Prevent simulation speed from changing the six-second freshness rule. Define the reseeding policy when new evidence arrives.

The five-second communications test may end before observations become stale. Use the separate live visual-loss demonstration to trigger drift growth. Any hidden simulated reference trajectory used for evaluation stays outside the estimator inputs.

## Functional requirements and traceability

Accepted behavior is identified by decision IDs. Rows marked engineering contract describe implementation safeguards derived from that behavior.

| ID | Requirement | Basis | Verification |
| --- | --- | --- | --- |
| FR-01 | MOB starts one incident and automatic candidate detection on both nodes | D-32 | V-01 |
| FR-02 | Observations preserve node, incident, capture time, target association, image reference, location quality and provenance | Engineering contract supporting D-16, D-21, D-23 | V-01, V-06 |
| FR-03 | Ground processing retains observations through the coordinator-link outage | D-28, D-41 | V-02 |
| FR-04 | Each node retains last valid screen grab, location and advancing age through loss states | D-14, D-16, D-21, D-26 | V-02, V-03 |
| FR-05 | Distinguish visual contact loss, video-input loss and unavailable coordinator link | D-14, D-41 | V-03 |
| FR-06 | Show the labeled drift estimate when neither sighting is fresh, with last locations and environmental provenance visible | D-22–24, D-43–44 | V-04 |
| FR-07 | Restore newest observation and video before timestamped backlog | D-30, D-45 | V-05 |
| FR-08 | Duplicate, reordered or restarted-source messages cannot rewind current state or recreate an incident | Engineering contract supporting D-30 | V-05 |
| FR-09 | Apply the inclusive 50 m association/reacquisition rules and confirmation fallback | D-17–20, D-33 | V-07 |
| FR-10 | Support the agreed internet-connected deployment and independent local failure injection | D-31, D-41 | V-08 |
| FR-11 | Initial confirmation starts tracking and following. Expose stop/override | D-16, D-27, D-32 | V-01, V-10 |
| FR-12 | Show both live feeds with the accepted fallback evidence | D-25–26, D-36 | V-09 |
| FR-13 | Follow with configured geometry, hold on visual loss and yield to aircraft failsafe | D-29, D-37–40 | V-10 |
| FR-14 | End Incident stops mission activity, preserves history and hands recovery to operator | D-46 | V-11 |
| FR-15 | Enable optional thermal only after hardware-specific software verification | D-11 | V-12 |

## Provisional performance targets

| Measure | Target or rule | Measurement boundary |
| --- | --- | --- |
| Acquisition | <= 5 seconds per node | Person becomes clearly visible during active MOB to candidate appearing on coordinator display |
| Live video | >= 10 displayed FPS per feed | Both feeds running simultaneously under recorded venue conditions |
| Video latency | <= 1 second | Frame capture to coordinator display |
| Freshness | Stale when age > 6 real seconds | Last accepted sighting capture time, never refreshed by a heartbeat or delayed delivery |
| Coordinator outage | 5 real seconds | Processor-to-display path interrupted |
| Recovery | <= 3 seconds | Usable coordinator connection returns to current observations and both available feeds restored |
| Association radius | <= 50 m accepted automatically | Horizontal person-to-person distance under the applicable reference rule |
| Following | Operator-configured separation, altitude and image region | Record setpoints, tolerances, target motion and aircraft mode before testing |

Acquisition, video and recovery targets are provisional and hardware-dependent. Record actual results and agree revisions explicitly. Observation cadence near three seconds remains an unaccepted proposal, independent of continuous video. Heartbeat cadence and link-loss timeout must allow the five-second outage to be visibly demonstrated and remain to be selected.

## Hardware and implementation gates

| Gate | Required evidence | Accepted fallback or open decision |
| --- | --- | --- |
| Aircraft and video path | Exact model/revision, control API, video receiver/capture, camera mounting, pilot and flight slot | Pilot assistance if autonomy unsupported |
| Autonomy and hold/search | Supported command interface, position source, fixed-camera control behavior and tested override/failsafe | Clearly label operator-performed functions |
| Crazyflie option | Compatible radio, positioning and camera accessories | Availability remains unverified |
| Person geolocation | Calibrated geometry/pose or other validated method | Clearly labeled simulated person coordinates |
| Accelerator | Exact model, runtime, compatible detector, two-feed benchmark | Select compatible compute implementation after checkout |
| Thermal | Device, driver/SDK, format, preprocessing, model and live test | Optional |
| Drift | Named model, dataset/license, source/location/time, assumptions and simulation clock mapping | Selection pending |
| Ownership | One implementation/integration owner and flight operator identified | Single implementation workstream accepted |

Autonomous takeoff and initial search were discussed but remain unresolved. Keep them outside claimed demonstrated autonomy until explicitly defined and supported. Automated following starts after coordinator confirmation. Runtime versions, capture dimensions, venue test conditions and deployment endpoints are implementation choices to record during bring-up.

## Build and acceptance

Follow the ordered build sequence in [software](../engineering/software.md) and complete the [acceptance checklist](../engineering/verification.md). The implementation owner owns software integration and evidence collection. The flight operator owns aircraft setup and recovery. Names remain to be recorded.

The organizer cutoff is **November 8, 2026 at noon EST**. Use the [event constraints](event-constraints.md). No implementation or measured hardware result is claimed by this PRD.

## Interview decision register

Later decisions refine earlier wording where noted. This register preserves the interview history. The consolidated requirements above define the current baseline.

| ID | Decision | Status and basis |
| --- | --- | --- |
| D-01 | Open-ocean man-overboard scenario | Confirmed by user |
| D-02 | Manual declaration starts the initial demo | Confirmed through D-32 |
| D-03 | Preserve position, image evidence and observation age through outages | Confirmed through D-16, D-21 and D-26 |
| D-04 | Interview one question at a time | Confirmed by user |
| D-05 | The search-and-rescue coordinator is the primary demo user and directs the single responding ship | Confirmed by user |
| D-06 | Two sensor nodes observing one person overboard. One is a drone, and the other is a camera acting as a proxy for a second drone due to resource constraints | Confirmed by user. Independent node operation is defined in D-21 |
| D-07 | Approximately three-second periodic updates | Discussed proposal. Timing target to confirm |
| D-08 | Live detection and tracking must support real-time aircraft following and automatic camera pointing at the person | Refined by D-40. Fixed-camera following and labeled pilot assistance are accepted |
| D-09 | Flight access is confirmed by the user. The demo includes an airborne drone with following as refined by D-40. The second node is a live phone or other camera standing in for another drone | Confirmed by user. Aircraft control and camera interfaces still require verification |
| D-10 | Use real person geolocation when available. Otherwise, clearly labeled simulated person coordinates are acceptable alongside live detections | Confirmed by user. Coordinate frame and geolocation implementation remain open |
| D-11 | Visible-light cameras are sufficient for both nodes. Thermal imaging is optional when hardware is available and requires software compatible with the selected thermal device and imagery | Confirmed by user. Verify driver/SDK, stream format, preprocessing and thermal detection/tracking before enabling the option. Video replay excluded by D-15 |
| D-12 | One person uses Claude or Codex to build and integrate the system through a single implementation workstream | Confirmed by user. Named owner, physical hardware checkout support and software versions remain open |
| D-13 | A verbal direction from the coordinator is outside the initial demo acceptance criteria | Confirmed by user |
| D-14 | The demo distinguishes visual loss on a healthy link from radio loss with unknown current visual status. Both states retain the last sighting and its age | Confirmed by user |
| D-15 | Retain the last known screen grab with a valid MOB detection or the last known location. Video replay is excluded from the demo | Confirmed by user. Initial confirmation and subsequent updates are defined in D-16 |
| D-16 | The coordinator confirms the initial detection as the person overboard. The last screen grab and location then update automatically while that person is tracked | Confirmed by user |
| D-17 | Reacquisition within a provisional 50 m radius of the previous acquisition resumes updates without coordinator reconfirmation. The operator can divert the drone away from an incorrect target | Confirmed by user. Location quality and diversion mechanism need definition. D-19 defines the distance reference and boundary. D-18 defines behavior outside the radius |
| D-18 | Reacquisition beyond 50 m requires coordinator confirmation before replacing the retained sighting. Until confirmation, show the new candidate and retain the previous sighting | Confirmed by user |
| D-19 | Center the reacquisition radius on the last observed location of the person immediately before visual loss. Horizontal distance of 50 m or less, including exactly 50 m, resumes updates automatically. Greater distances follow D-18 | Confirmed by user |
| D-20 | Missing or unreliable location data requires coordinator confirmation of a reacquired candidate. Keep the last sighting visible until confirmation | Confirmed by user |
| D-21 | Both nodes independently detect and track the person and report to the same coordinator display. Each node has its own visible last sighting, observation age and loss state | Confirmed by user |
| D-22 | When neither node has a fresh sighting, show a growing estimated search area using drift prediction modeling data. Keep both last observed locations visible and clearly label the area as an estimate | Confirmed by user. Model, dataset and uncertainty calculation remain open. D-24 defines freshness |
| D-23 | Preloaded wind and ocean-current data are acceptable for the demo. Show their source, location and time, and calculate the drift estimate using the latest observations | Confirmed by user. Dataset selection remains open |
| D-24 | A sighting becomes stale when its capture age exceeds six seconds. Show the estimated search area when both nodes have stale sightings | Confirmed by user as a provisional demo threshold |
| D-25 | Video streams continuously. Observation freshness uses the capture time of the last valid sighting | Continuous video confirmed by user. D-26 defines display behavior and D-36 defines provisional video targets. Transport remains open |
| D-26 | Show both live feeds simultaneously on the coordinator display when their links are available. When a node video is unavailable, show its last valid screen grab, location, observation age and status | Confirmed by user. Previously accepted last-sighting visibility during visual loss also applies |
| D-27 | Coordinator confirmation of the initial target starts autonomous aircraft following and camera pointing. Provide an explicit stop or override control | Confirmed by user. Camera pointing refined by D-40. Control interface and override behavior require verification |
| D-28 | During loss of the coordinator video/data link, continue following while onboard tracking and the pilot control link remain healthy. Retain observations for reconnection. Show link loss and the last received sighting age on the coordinator display | Demo processing boundary refined by D-41. D-38 defines pilot-link loss behavior |
| D-29 | On visual loss, hold aircraft position while the camera searches. Resume following after reacquisition under the agreed 50 m and coordinator-confirmation rules | Confirmed by user. D-40 permits fixed-camera following. Hold/search compatibility is a hardware gate |
| D-30 | On reconnection, prioritize the newest observation and live video, then transfer older observations as timestamped history. Older observations must not overwrite newer sightings | Confirmed by user |
| D-31 | Internet access is available for the demo. Full offline operation is not required | Confirmed by user |
| D-32 | MOB declaration starts automatic candidate detection on both nodes. Coordinator confirmation selects the person and starts tracking and aircraft following | Confirmed by user |
| D-33 | The second node automatically associates its detection with the confirmed person when geographically feasible, without separate coordinator confirmation | Confirmed by user. Automatically associate detections within 50 m inclusive of the most recent accepted person location. Greater distances or missing/unreliable coordinates require coordinator confirmation |
| D-34 | Demonstrate live person detection at the venue using a person on land. Clearly label the ocean coordinates and drift scenario | Confirmed by user. This demonstration does not establish measured open-ocean detection performance |
| D-35 | Each node must display a candidate within five seconds of the person becoming clearly visible during an active MOB incident, under agreed venue conditions. Timing ends when the candidate appears on the coordinator display | Confirmed by user as a provisional acceptance target. Lighting, distance and camera conditions remain to be specified |
| D-36 | Target at least 10 displayed frames per second per live feed and capture-to-display latency of one second or less, with both feeds running simultaneously | Accepted provisionally, subject to actual hardware constraints. Benchmark the integrated system and record achievable values before finalizing thresholds |
| D-37 | Autonomous following maintains configured separation and altitude while keeping the person centered in the camera view. Set distances with the flight operator for the aircraft and venue. State in the demo that real-world separation and altitude would vary with operating conditions | Confirmed by user. Distances and tracking tolerances await aircraft and venue assessment |
| D-38 | Loss of the pilot control link yields to the aircraft configured failsafe | Confirmed by user |
| D-39 | Prefer autonomous operation from the start. Verify the available aircraft technical specifications and interfaces. If autonomous operation is unsupported, use a pilot for the demo | Confirmed by user. Six available aircraft models supplied by user and reviewed in hardware.md. Crazyflie accessory availability remains unresolved. Autonomous launch/search scope still needs clarification |
| D-40 | Aircraft following with a fixed camera that keeps the person within a defined central image region is accepted in place of independent automatic camera pointing. Use autonomous operation where supported and clearly identify pilot assistance otherwise | Confirmed by user. Image-region tolerance and actual control support require testing |
| D-41 | Process drone video on the ground. The coordinator-outage test interrupts only the processor-to-display link, while processing continues. Loss of the drone-to-processor video link is visual-input loss | Confirmed by user. This refines the onboard-processing assumption in D-28 for the demo |
| D-42 | Use a five-second processor-to-display link outage for the demo | Confirmed by user. D-45 defines the accepted provisional recovery target. A five-second outage may end before both observations exceed the six-second freshness threshold |
| D-43 | Hide the person from the live cameras and use a concurrent, clearly labeled ocean simulation to demonstrate the growing drift estimate. Preserve the last observed locations and derive the estimate using the accepted environmental inputs | Confirmed by user. Visual-loss duration remains configurable. D-44 defines accelerated simulation |
| D-44 | Use a clearly labeled accelerated clock for drift simulation, displaying simulated elapsed time and speed. Live video and outage timers remain in real time | Confirmed by user. Simulation speed remains configurable |
| D-45 | Restore current observations and both available live feeds within three seconds after usable coordinator connectivity returns | Confirmed by user as a provisional target subject to hardware testing |
| D-46 | End Incident stops tracking and following, preserves incident history and hands aircraft recovery to the flight operator | Confirmed by user |
| D-47 | Use a Python backend and browser-based coordinator display in the same repository. Select hardware-specific adapters after device checkout | Confirmed by user |
