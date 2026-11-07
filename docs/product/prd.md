# Product requirements — working draft

Updated November 7, 2026. Status is discovery. The user requested a rigorous PRD interview conducted one question at a time. This draft organizes the evidence and proposed requirements so the team can resolve them.

## Problem and intended outcome

In an open-ocean man-overboard incident, the ship and rescue boat need timely evidence of where the person is. The drone may keep observing while communications fail. It may also lose visual contact while communications remain healthy. A shared display must represent what is known, when it was observed, and how uncertain the current estimate is.

The proposed outcome is shorter acquisition and information-recovery time with useful location evidence maintained through interruption. Performance claims require measurements under explicit conditions.

## Evidence and decisions

| ID | Decision | Status and basis |
| --- | --- | --- |
| D-01 | Open-ocean man-overboard scenario | Confirmed by user |
| D-02 | Manual declaration starts the initial demo | Supported by both team discussions |
| D-03 | Preserve position, image evidence and observation age through outages | Supported direction in the discussions |
| D-04 | Interview one question at a time | Confirmed by user |
| D-05 | Primary user is ship coordinator or rescue boat operator | Open. Current interview question |
| D-06 | One target and one camera node as the baseline | Proposed scope |
| D-07 | Approximately three-second periodic updates | Discussed proposal. Timing target to confirm |
| D-08 | Required live capture, automatic detection, tracking and physical pointing | Open. Each capability needs a separate acceptance condition |
| D-09 | Aircraft flight, additional nodes and robot demonstration | Optional ideas awaiting hardware and scope decisions |
| D-10 | Usable GNSS/pose for the ocean scenario; local coordinates for indoor tests | Proposed assumption. Validate against event expectations |
| D-11 | Thermal input, RGB fallback, replay allowance | Open |
| D-12 | Team roles, integration owner and software versions | Open |

## Candidate functional requirements

All requirements below are proposed until accepted in the interview. IDs support implementation and test traceability.

| ID | Observable behavior | Verification |
| --- | --- | --- |
| FR-01 | A manual declaration creates one incident and begins observation handling | V-01 |
| FR-02 | Each observation identifies source, target association, capture time, visual state, evidence provenance and location quality | V-01, V-06 |
| FR-03 | Edge processing and local retention continue during a data-link outage | V-02 |
| FR-04 | The operator sees observation age and link age independently | V-02, V-03 |
| FR-05 | Fresh reported visual loss is distinguishable from an unreachable node | V-03 |
| FR-06 | A last observed location remains separate from a predicted present location and uncertainty region | V-04 |
| FR-07 | Reconnection applies the freshest state and preserves older evidence as history | V-05 |
| FR-08 | Duplicates, reordered packets and source restarts do not create false incidents or rewind the current state | V-05 |
| FR-09 | Reacquisition preserves ambiguity when target identity is uncertain | V-07 |
| FR-10 | Operator evidence remains available on the local network without cloud services | V-08 |

## Engineering quality requirements to quantify

| Concern | Required decision or measurement |
| --- | --- |
| Acquisition | Start/stop definition, target size, camera geometry, input modality and acceptable delay |
| Tracking | Definition of lock, visible-frame coverage, false associations and tolerated visual gap |
| Geolocation | Coordinate frame, reference surface, calibrated pose/time error and acceptable position error |
| Communications | Payload size, update cadence, latency distribution, dropout/reorder pattern and image policy |
| Recovery | Maximum recovery delay after usable link returns and persistence across restart |
| Resources | Frame rate, CPU/RAM, power and runtime on the actual target device |
| Uncertainty | Envelope construction, empirical coverage and area under a specified scenario distribution |
| Usability | Correct interpretation of stale evidence and action the primary operator takes |

Set thresholds after a short baseline measurement and explicit team agreement. A scenario's configured value is not a measured performance result.

## Proposed demo boundary

The initial slice is declaration, one camera observation path, target state, timestamped evidence delivery, link interruption and recovery. A distinct visual-loss case exercises the second failure mode.

The long-term vision includes rapid drone launch, autonomous search, physical camera/aircraft following and rescue delivery. These require separate scope decisions and interfaces. A tracked image box alone establishes image tracking. Radio transport alone supplies no calibrated location estimate.

## Acceptance and open interview sequence

Use the [verification matrix](../engineering/verification.md). Each accepted requirement must have an owner, defined input conditions, a threshold or expected result, and recorded evidence.

The next unanswered question is whether the primary user is the ship's coordinator or the rescue boat operator. Then establish required demo behaviors, available physical inputs, localization assumptions, measurable timing/error budgets, failure handling and team ownership. Recompute dependent questions after each answer.
