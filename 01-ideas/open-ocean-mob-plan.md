# Open-ocean man-overboard response

Research and proposed hackathon scope, November 7, 2026.

## Intent captured from the team

The [Granola meeting](https://notes.granola.ai/d/d8470afa-fe9b-4ce5-a3cc-e39d5fc32f79), including all three transcript chunks, describes rapid acquisition after a man-overboard declaration, continued drone observation, and a shared picture for the ship. Participants discussed an approximately three-second update carrying position, image, and visual-contact status. They explicitly distinguished losing the communications link from losing visual contact. The last observation should remain useful if the drone disconnects or becomes unavailable.

The fall-detection trigger was treated as a separate problem. Swarms, an aircraft strobe, and drift-informed initial search were discussed as possibilities. The team had not settled a final implementation. The suggestion that lock-on covers 90% of scenarios was conversational speculation and supplies no performance evidence.

This proposal adopts the user's subsequent open-ocean requirement. Previous harbor maps illustrate the interface only. The scenario begins with a declared incident, approximate fall position and time, one person, one drone, a mother ship, and one rescue boat. It assumes usable aircraft and vessel position/attitude telemetry for the baseline. Loss of cellular service is compatible with this assumption. GPS denial would require a separate relative-localization capability and should be recorded as an unresolved extension.

## First principles

1. **A rescue requires timely relative location.** The boat operator needs the person's estimated position relative to the boat, observation age, and uncertainty. Global coordinates are useful for sharing but depend on a valid reference frame.
2. **A camera measures image coordinates.** A bounding box supplies a viewing direction. Converting it to position needs camera calibration, aircraft position and attitude, gimbal angles, altitude above the water, and synchronized timestamps. A flat local sea-plane intersection is a reasonable short-range demo assumption. Waves, pose errors, and nearly horizontal views increase error. The aircraft's GPS position alone cannot locate the person. [OpenCV camera geometry](https://docs.opencv.org/4.7.0/d9/d0c/group__calib3d.html)
3. **The target moves between observations.** Start with a local position/velocity state and uncertainty. Observed motion can estimate short-term velocity when the world-coordinate observations are trustworthy. Current and wind-driven leeway provide additional motion hypotheses. Zero current is an assumption, not missing-data handling. [OpenDrift Leeway](https://opendrift.github.io/autoapi/opendrift/models/leeway/index.html)
4. **Video tracking, camera pointing, and flight control are different tasks.** A persistent box demonstrates image tracking. Keeping the target in view requires gimbal or aircraft control. An aircraft-following demo additionally needs supported autopilot integration and flight testing. The prototype must identify which of these it actually implements.
5. **Observation and communication can fail independently.** A fresh heartbeat reporting visual loss differs from a link outage. During silence the ship knows only the last reported drone state. Local drone evidence may continue accumulating.
6. **Bandwidth should preserve the most actionable evidence first.** Send compact state updates periodically and immediately on state changes. Associate thumbnails with their own capture timestamps. A delayed image must never make an old observation appear current.
7. **Identity remains uncertain after a gap.** A reacquired bright object could be another object. Use position consistency and operator review when association is ambiguous. An object detector's confidence is distinct from position uncertainty and track identity.

Thermal feasibility depends on exposed target size, contrast, lens, altitude and sea state. A marine pilot study specifically investigated low contrast and altitude limits. A daytime camera demonstration establishes the communications/tracking workflow only for its tested imagery. [Thermal pilot study](https://www.mdpi.com/2504-446X/8/3/76)

## Feasible directions

| Direction | Concrete demonstration | Main integration risk | Recommendation |
| --- | --- | --- | --- |
| Acquisition and visual tracking | Detect a candidate in real video and retain its track | Tiny thermal targets, weights, camera access, physical pointing | Include one working input if available |
| Shared contact during interrupted communications | Drone keeps processing while the ship ages its last update, then reconciles on reconnect | Timestamp semantics and honest operator states | Core hackathon contribution |
| Autonomous drift-directed search | Choose and execute the next flight search leg | Reliable drift forcing, telemetry and aircraft control | Later extension |

The proposed contribution is an evidence-aware handoff between a drone and a boat under limited communications. Novelty is a hypothesis to test with mentors and operators. Existing tracking, drift forecasting and mission systems already cover substantial parts of the problem.

## Proposed minimum implementation

Run an edge process on the Pi and an operator display on a laptop. Use a local link and a controllable packet-loss relay. The edge process consumes live camera frames or labeled video replay, maintains a target track, and stores observations locally. A boat-side process stores received updates and predicts forward from the freshest observation it has actually received. Use a prerecorded open-ocean trajectory with separately labeled simulated telemetry when camera pose is unavailable.

The base packet contains incident ID, source ID, source-session ID, sequence number, observation time, transmission time, track ID, visual state, location/reference frame, position uncertainty, and a thumbnail reference/capture time. The receiver adds receipt time. Preserve missing locations as unknown. Sequence numbers and timestamps handle duplicates, late delivery and source restarts. Reconnect sends the freshest state first and historical observations afterward without rewinding the operator view. Clock offset must be measured or an explicit simulated-clock assumption recorded.

Start with a three-second periodic update as discussed in the meeting, plus immediate visual-state changes. Treat three seconds as a tunable demo setting. Record packet and image byte counts. For illustration, a 20 kB thumbnail every three seconds alone needs about 53 kb/s before overhead. Small LoRa messages and video/images have very different transport needs.

The operator screen shows observation age, link age, last reported visual status, last observed position, a separately identified predicted search area, last image with capture time, and bearing/range from the rescue boat if its position is known. Show a direction cue without claiming a collision-aware navigation route. The open-ocean map should emphasize vessel motion, distance scale, bearings and uncertainty rather than nearby landmarks.

### Required state behavior

| Received evidence | Boat-side display |
| --- | --- |
| Fresh visual observation | Contact observed at its capture time |
| Fresh heartbeat, visual lost | Drone connected, target unobserved |
| No recent messages | Link stale, current drone visual state unknown |
| Reconnection with fresh observation | Update location and observation age |
| Old buffered image arrives | Historical image with original age |
| Ambiguous reacquisition | Candidate pending review |

For short outages, a constant-velocity predictor with an uncertainty envelope is sufficient to test the workflow. If current is modeled separately from velocity inferred from positions, avoid counting the same drift twice. A heuristic envelope must be labeled as a scenario assumption. Call it a 95% region only after calibration and coverage testing.

## Public repositories and practical use

Inspected November 7. Repository documentation review establishes available components, not successful local installation or measured compatibility. Pin selected versions after the first working run. Code, pretrained weights and datasets may have different terms.

| Repository | Reusable component | Integration assessment |
| --- | --- | --- |
| [Hailo Pi examples](https://github.com/hailo-ai/hailo-rpi5-examples) | Pi detection pipelines and detection callbacks | Best hardware starting point if the supplied accelerator is Hailo-8/8L and its installed image matches. First run the vendor example unchanged. Generic model performance on swimmers remains to be measured. |
| [Roboflow trackers](https://github.com/roboflow/trackers) and [Supervision](https://github.com/roboflow/supervision) | Detection association, video annotations and processing | Useful around an existing detector. Current docs move ByteTrack to the trackers package. Supervision is MIT. Verify tracker and model terms for the pinned versions. |
| [FoundationVision ByteTrack](https://github.com/FoundationVision/ByteTrack) | Original MIT tracking implementation and examples | Reference for association. Its published speed is GPU/benchmark-specific. Image-space tracking needs a separate world-coordinate estimator. |
| [DSTL Stone Soup](https://github.com/dstl/Stone-Soup) | MIT tracking and state estimation framework | Suitable for missed-measurement and uncertainty experiments. Adopt one simple example if it reduces work. A full framework is optional for the demo. |
| [OpenDrift](https://github.com/OpenDrift/opendrift) | GPL-2.0 ocean trajectory framework with Leeway SAR model | Best physics reference or offline scenario generator. Scientific dependencies and wind/current inputs add integration work. Official install recommends a dedicated conda/mamba environment. |
| [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) | MAVSDK Python client with vehicle examples | Optional telemetry integration for compatible MAVLink aircraft. Availability of a drone does not establish SDK compatibility. Pi may need a separately running mavsdk_server. |
| [SeaDronesSee](https://github.com/Ben93kie/SeaDronesSee) | Maritime video benchmark, evaluation kits and model examples | Good RGB replay/evaluation source. Its single-object tracking protocol describes targets staying visible throughout clips, so add explicit loss/reacquisition tests for this task. Confirm dataset terms separately. |
| [MOBDrone evaluation](https://github.com/ciampluca/MOBDrone_eval) | Evaluation notebook using saved predictions and dataset images | Useful for measuring detection. The README does not provide a ready live detector. Repository code license was not established in this review. |

Current [Supervision tracking documentation](https://supervision.roboflow.com/latest/how_to/track_objects/) states that sv.ByteTrack was removed in version 0.31.0 and uses ByteTrackTracker. Avoid combining older examples with an unpinned current install. The original [Hailo infrastructure repository](https://github.com/hailo-ai/hailo-apps-infra) now redirects to hailo-apps, making the supplied device's working image the most useful starting point.

Two research leads should not gate delivery. The [PDMS man-overboard repository](https://github.com/DTU-IPL/pdms-man-overboard) currently exposes only a README promising a later code release. The [MAMMS dataset](https://zenodo.org/records/17979190) has thermal UAV sequences and a geolocation subset with ground truth and telemetry, but downloads require a user agreement and a supplied link. Access turnaround was not established.

## Demo and measurement plan

Use one scripted open-ocean incident with a separate ground-truth trajectory. Label replay, live hardware, and simulated telemetry independently.

1. Declare the incident and acquire a target. Show video evidence, target state and update arrival on the laptop.
2. Interrupt only the data link for 15 seconds. Show local processing continuing and the ship's received observation aging.
3. Restore the link. Deliver a current observation, duplicates, and an older thumbnail. Demonstrate that the live view remains current and retains history.
4. Interrupt visual observations while keeping the link active. Show the distinct visual-loss state.
5. Reintroduce the target and a distractor. Record correct reacquisition, operator review and any identity switches.

Compare the same trajectories and packet schedules against a receiver that simply holds its last position. Measure position error in meters, envelope area, empirical coverage across trials, observation age, recovery latency, bytes transferred, false detections, and identity switches. A predictor can perform worse when its drift assumption is wrong, so include a changed-current case. Compare equal conditions and report all runs rather than one favorable replay.

The strongest visible result is two concurrent displays. The edge display continues tracking during the outage while the boat display explicitly shows the age and limits of its information, then recovers cleanly. A stationary-camera or pan-tilt demo can establish those behaviors. Aircraft tracking in open-ocean conditions remains a separate validation step.

## Build order and decision gates

1. **First hour** — Identify camera model, output stream, accelerator model/image, and accessible telemetry. Run one existing capture/detection example. If thermal imagery cannot be acquired, choose documented RGB replay for the workflow and retain thermal as a later input.
2. **Next 2–3 hours** — Complete observation producer, timestamped packets, receiver storage, and an open-ocean operator view with one target.
3. **Next 2 hours** — Add outage injection, prediction, reconnect handling, and the separate visual-loss case.
4. **Following 1–2 hours** — Connect the actual camera/Pi path if not already working. Add a pan-tilt or status LED only if its driver and power setup are ready.
5. **Reserve the remaining time** — Run repeatable comparisons, rehearse, record a backup, and prepare the organizer submission. These are planning estimates, not measured setup times. Sunday November 8 at noon EST is the recorded cutoff.

Potential parallel ownership within a team is perception, transport/storage, operator interface, and scenario/evaluation. One person should own integration. Team size and assignments remain unconfirmed.

The next scope decisions are the available camera and its stream, whether drone telemetry can be read, whether baseline GNSS is acceptable to the judges, and which live hardware contribution can be demonstrated reliably. Validate the handoff workflow with an available maritime operator or mentor before investing in autonomous flight.
