# Drone swarm demo planning

November 7, 2026 at 12:35 PM EST. Curated team notes from the Granola summary and checked transcript passages. The transcript supplies speaker letters and no reliable per-turn timestamps. Individual task owners remain unassigned where speaker identity is unclear. [Original Granola meeting](https://notes.granola.ai/d/85a57ba3-e40f-4b8b-b273-57acbbdc1880)

## Mission and longer-term vision

Reduce the time from a person going overboard to acquisition, confirmed lock and maintained awareness. Participants emphasized multiple viewpoints to improve continuity through occlusion, limited battery life and connectivity interruptions.

The broader vision connects aerial search and tracking with surface-vessel recovery. Participants discussed larger swarms, rapid launch and automatic fall detection as future capabilities. The venue demonstration focuses on acquisition and maintained contact with one person. Ship maneuvering and verbal directions are outside the initial demonstration.

## Live demonstration

- Use two sensor nodes, an airborne quadcopter and a person holding a phone or another live camera as a proxy for a second drone.
- Declare MOB manually and detect candidates automatically.
- Have the coordinator confirm the initial person, then track and follow.
- Show both live feeds simultaneously. Retain the last valid screen grab, person location and sighting age when a feed is unavailable.
- Distinguish visual loss from communications loss. Sightings become stale after six seconds.
- Reacquire automatically within the agreed 50 m radius. Require confirmation outside the radius or when location information is inadequate.
- Associate the second node automatically when geographically feasible.
- Hold the aircraft on visual loss for the venue demonstration. The indoor space limits the search motion that can be demonstrated physically.
- Use fixed-camera aircraft tracking/following where supported, with pilot assistance if hardware autonomy is insufficient.
- End Incident stops tracking/following, preserves history and hands recovery to the flight operator.

The discussion reduced the proposed coordinator outage from 15 seconds to five seconds for pacing. Video processing may run on the ground, with the outage injected between processor and coordinator display. The accepted recovery target is documented in the PRD.

## Concurrent ocean simulation

Run an ocean scenario alongside the live venue demonstration so viewers can connect live acquisition with the intended maritime workflow.

The proposed visual sequence is a person entering the water, an uncertainty area expanding, acquisition shrinking the area, loss of contact expanding it again, and a simulated drone following a drift-informed search before reacquisition.

Use preloaded wind and ocean-current data and the last known person location. Present the map and search region clearly with limited dashboard clutter. Clearly distinguish the indoor live demonstration from simulated ocean motion and search behavior. Simulated person coordinates are acceptable alongside live detections when real geolocation is unavailable.

## Hardware updates reported in the meeting

| Item | Discussion record |
| --- | --- |
| Quadcopter checkout | Participants reported that available aircraft had already been checked out. They proposed approaching Stefan, the organizer contact, for a loan and discussed borrowing or purchasing as alternatives |
| Flight space | A participant relayed that indoor flight space was available. Exact arrangements and demonstration access still needed coordination |
| Depth camera | A participant reported obtaining a depth camera. Its model and actual measurement performance were not established in the discussion |
| Thermal | Optional for the demo. Participants reported thermal hardware at rooms or stations 28, 30 and 32 and discussed asking the desk about access |
| Radios | Participants reported that LoRa/radio units were checked out. Wi-Fi was proposed as the demonstration transport |
| Aircraft candidates | The team read out EMAX Tinyhawk II, BETAFPV Aquila16, NewBeeDrone VRDrone, EMAX Tinyhawk Lite, BETAFPV Cetus X and Crazyflie. Exact accessories and control support needed checking |

Participants expressed confidence that flight access could be arranged. These logistics reports describe the situation during the meeting and should be checked against the actual checkout record.

## Build strategy

The team compared four parallel implementation streams with one computer handling the initial build. The final starting plan was one person implementing the system, with parallel work considered if bottlenecks arise.

Use a Python backend and browser-based coordinator display in the shared repository. Publish the completed PRD, then have the coding agent produce an implementation plan before building. Discussion separated perception, flight/hardware, display/simulation and integration responsibilities conceptually.

A participant offered to focus on UI, camera-node connectivity and the common operating picture. Drone bring-up was identified as work that could proceed separately. The transcript does not reliably identify the owner of that offer.

## Next steps discussed

- Publish the PRD and generate an implementation plan before starting the build.
- Ask the organizer contact about a quadcopter loan and confirm indoor flight arrangements.
- Identify the exact drone model, accessories, autonomous control capability and live video capture path.
- Inspect the acquired depth camera and run its supported capture example.
- Check thermal availability if it can be integrated within the demo schedule.
- Establish the live camera and coordinator path on one implementation machine, then revisit parallel work if needed.

## Engineering interpretation and evidence limits

These clarifications distinguish discussion claims from verified capabilities.

- A participant suggested Crazyflie might provide automatic camera pointing. The repository hardware review makes autonomy conditional on compatible positioning, camera and radio accessories plus implemented control software. Follow the current hardware gates.
- A depth-camera description was paraphrased as millimeter-accurate. Treat that as an unverified device claim until model, range, calibration and measurements are recorded.
- A thermal-looking filter on visible-light video was suggested as a visual effect. It supplies no thermal measurements. Any such effect needs a simulation label. The PRD thermal option requires actual compatible thermal hardware and software.
- Multiple viewpoints were discussed as improving continuity. Assertions of nearly guaranteed contact or novelty remain unmeasured hypotheses.
- Wi-Fi demonstrates the selected message and video path. LoRa throughput, range and failure behavior require separate hardware evidence.
- Simulated drift-guided flight illustrates the longer-term concept. Physical flight commands must use validated venue inputs and the aircraft-specific control path.

The [PRD](../product/prd.md) holds accepted product decisions. The [hardware review](../engineering/hardware.md) and [verification checklist](../engineering/verification.md) define remaining integration gates and evidence.
