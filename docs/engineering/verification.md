# Verification and demonstration

Each case maps to proposed PRD requirements. Results are pending. Thresholds, test conditions and owners must be accepted before implementation claims.

| Case | Requirements | Procedure and evidence |
| --- | --- | --- |
| V-01 Incident and observation | FR-01, FR-02 | Declare one incident, ingest a labeled observation and inspect identity, timestamps and provenance at receiver |
| V-02 Link outage | FR-03, FR-04 | Drop only communications for a configured interval; verify edge processing continues, receiver ages evidence, and data persist |
| V-03 Visual loss | FR-04, FR-05 | Keep heartbeats flowing while hiding the target; verify visual loss is distinct from stale link |
| V-04 Estimation | FR-06 | Replay a held-out trajectory; measure error, region area and coverage against fixed last-seen baseline, including wrong-drift conditions |
| V-05 Recovery and ordering | FR-07, FR-08 | Reconnect with fresh data, duplicates, late images and restarted source; verify newest state and preserved history |
| V-06 Invalid geometry/time | FR-02 | Omit pose or invalidate clock assumptions; verify unknown/degraded quality instead of invented location or age |
| V-07 Reacquisition | FR-09 | Reintroduce the target and a distractor; record identity switches, false contacts and review decisions |
| V-08 Local operation | FR-10 | Cold-start without Internet using cached assets; separately test loss of local network |

## Measurements

Record acquisition-time definition, source frame rate, capture-to-display latency, observation age, reconnect latency, transferred bytes, location error, track continuity and false associations. Record the platform, input modality, camera geometry, outage schedule and model versions alongside results.

Measure predicted-region coverage together with area. A large region can contain the person while being operationally unhelpful. Report confidence percentages only when calibrated against a stated population of trials.

Use independent or held-out ground truth. Do not generate observations and predictions from the same perfect trajectory and call the result validated performance. Include all planned trials and failures.

## Suggested demonstration

Show drone-side and ship-side views concurrently. Acquire a target, send periodic evidence, interrupt the link, restore it with out-of-order history, then interrupt only visual observations. Reacquire and show any ambiguity. Three seconds between updates and a 15-second outage are proposed exercise parameters.

A camera/Pi implementation can establish a real local observation and communication path. An ocean trajectory and unavailable aircraft telemetry can be labeled simulation. Record a backup video after the live sequence is reproducible.

Add executable tests under tests as components appear. Use small deterministic fixtures under fixtures. Put captured runs in ignored artifacts or recordings directories, and commit concise evidence reports when relevant.
