# Verification and demonstration

All results are pending. The single implementation owner records software evidence. The flight operator verifies aircraft-specific behavior. Identify both people and record devices, versions, conditions and mode before testing.

## Acceptance checklist

| Case | Requirements | Procedure and expected evidence |
| --- | --- | --- |
| V-01 Incident and confirmation | FR-01, FR-02, FR-11 | MOB starts both live candidate detectors. Confirm initial person and verify tracking/following activation. Record visibility-to-display time per node, provisionally <= 5 seconds. Preserve capture time, provenance and incident identity |
| V-02 Coordinator outage | FR-03, FR-04 | Interrupt only processor-to-display media/state for 5 real seconds. Show link loss, unknown remote visual state and retained evidence with advancing age. Demonstrate ground processing and retention continue with camera/control paths available |
| V-03 Visual and input loss | FR-04, FR-05 | Hide person with live frames and healthy coordinator link. Then separately stop drone video input. Verify distinct contact-loss/input-loss reporting, last accepted evidence and advancing age. Repeat with one healthy node to verify independent state |
| V-04 Drift and clocks | FR-06 | Hide person from both live cameras. Confirm freshness remains valid at exactly 6 seconds and becomes stale above 6 seconds. Show labeled wind/current-driven estimate, both last locations, environmental source/location/time, accelerated elapsed time and speed. Verify speed changes leave real video, freshness and outage clocks unaffected |
| V-05 Reconnection and ordering | FR-07, FR-08 | After the 5-second outage, restore current observations and both available feeds, provisionally within 3 seconds of usable connectivity. Then deliver backlog, duplicates, old images and restarted-source traffic. Verify history remains timestamped and current state never rewinds |
| V-06 Position and clock quality | FR-02 | Exercise real, simulated, missing and unreliable location states. Verify provenance and confirmation fallback. Invalid pose must not become an invented person location. Invalid clock alignment must be exposed |
| V-07 Association and reacquisition | FR-09 | Test 49.9, 50.0 and 50.1 m against the correct reference. First two auto-associate, last requires confirmation. Missing/unreliable reference or candidate location requires confirmation. Test initial cross-node association separately from same-node reacquisition. Retain prior evidence while pending |
| V-08 Deployment and isolation | FR-10 | Start the agreed internet-connected deployment and record dependencies. Verify outage injection affects only the intended coordinator path and does not accidentally read through a shared state store |
| V-09 Concurrent video | FR-12 | Run both live feeds simultaneously. Measure displayed FPS per feed and capture-to-display latency. Provisional targets are >= 10 FPS and <= 1 second. Verify each missing feed falls back to its retained screen grab, location, age and state |
| V-10 Aircraft control | FR-11, FR-13 | Record aircraft, operator, mode, separation/altitude and central-image-region tolerances. Verify follow, stop/override, visual-loss hold/search, valid reacquisition and configured pilot-link failsafe using an operator-approved test method. Clearly identify pilot-performed behavior |
| V-11 End Incident | FR-14 | End mission, verify tracking/following stop, history remains and recovery passes to operator. Delayed observations and retried commands must not restart the incident |
| V-12 Optional thermal | FR-15 | If enabled, record actual device, driver/SDK, format, preprocessing and model. Verify live capture, person detection and tracking through the same accepted observation path |

The 50 m tests use coordinate fixtures or the labeled scenario, with exact reference origins. Physical venue movement need not span 50 m. Software fixtures establish rule behavior. Live person detection remains required for the demonstration.

## Test record

For each case, record requirement IDs, input conditions, configuration, expected result, observed result, pass/fail, evidence path and reviewer. Record camera resolution/FPS, lighting, person distance and motion, host OS/CPU, accelerator runtime/model, aircraft revision and network arrangement.

Report sample counts and observed distributions for acquisition, FPS, latency and recovery. Finalize tolerances and trial counts before calling provisional targets met. Record CPU/RAM and concurrent processing load. Revisions to targets require an explicit decision and explanation.

For drift, record region area, prediction error and empirical coverage against independent scenario truth when available. Compare with a last-seen-location baseline. Vary current/wind assumptions and expose misses. An illustrative estimate may be presented with assumptions, while calibrated confidence percentages require evidence.

## Demo sequence

1. Identify the airborne node, live camera proxy, flight mode and real/simulated data labels. Show both live feeds.
2. Declare MOB, show automatic candidates, confirm the initial person and demonstrate following.
3. Demonstrate automatic association of the second node. Show both retained sightings.
4. Interrupt processor-to-display delivery for five seconds. Keep ground-side tracking visible separately for evidence. Restore current state/video and then history.
5. Hide the person from both cameras. Allow real sighting ages to exceed six seconds. Show the concurrent accelerated drift simulation, environmental provenance and growing estimated area.
6. Reacquire and exercise automatic acceptance and confirmation fallback using the configured scenario coordinates.
7. Use End Incident, show preserved history and hand recovery to the flight operator.

Choose visual-loss duration and simulation speed during rehearsal so the estimate is visible. Keep both clocks labeled. Runtime observations and archived history are evidence records. The demonstration uses live video.

## Completion gates

- [ ] Exact devices and adapters inventoried, including drone-video computer capture.
- [ ] Both live inputs tested independently and together.
- [ ] Baseline requirements exercised, with failures and revised targets recorded.
- [ ] Autonomous and pilot-assisted behavior labeled accurately.
- [ ] Drift model, environmental data, scenario mapping and provenance recorded.
- [ ] Acceptance evidence uses live detections and labels simulated coordinates.
- [ ] Dependencies pinned, startup documented and clean-checkout rehearsal completed.
- [ ] PRD, implementation and measured evidence reconciled before submission.

Tests should exercise lifecycle, timestamps, duplicate/reordered delivery, exact radius/freshness boundaries and clock separation. Add tests with implementation under tests and small labeled inputs under fixtures. Keep recordings, weights and databases out of Git by default.
