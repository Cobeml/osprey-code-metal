# PRD — Osprey: man-overboard response under degraded comms

Revised November 7, 2026 (evening) against verified hardware. Replaces the interview-era PRD; the original decision register is in git history (`87cc91e`). Organizer cutoff: **November 8, 2026, 12:00 EST** ([event constraints](event-constraints.md)).

## The story (what judges must understand in 30 seconds)

1. **A ship's deck camera sees someone go over the rail.** Nobody presses a button: the camera detects a person crossing the rail line and declares MAN OVERBOARD automatically, plotting the last-seen point.
2. **Scouts launch and search.** Two scout nodes (stand-ins for drones) look for the person. Until one finds them, the map shows a drift-driven search area growing from the overboard point.
3. **The coordinator confirms the person; scouts lock on and follow.** The search area collapses to a live position with evidence (screen grab, location, age) per scout.
4. **Comms degrade, the picture survives.** When the ship's link to the ground processor drops, the display freezes on the last evidence with an honest, ticking age. When the person is hidden from all scouts, the search area grows again from the last sighting.
5. **Reacquire and recover.** Contact resumes automatically when the new sighting is plausible (≤ 50 m), otherwise the coordinator decides. End Incident preserves everything.

Operator: the search-and-rescue coordinator on the responding ship. One screen, minimal controls.

## Nodes and hardware roles (verified Nov 7 unless marked)

| Role | Device | Status |
|---|---|---|
| Ground processor | Raspberry Pi 5 16 GB + Hailo-8 (fw 4.23, HailoRT 4.23) | Verified |
| **Ship deck camera** (trigger + real geometry) | Deptrum Aurora 930 RGB-D on the Pi, 640×400 @ ~14 fps, depth 0.3–3 m | Verified streaming |
| **Scout A** (mobile, physical following) | Hiwonder TurboPi rover, pan-tilt camera, labeled "ground stand-in for drone" | Not yet set up |
| **Scout B** (handheld proxy for second drone) | Phone browser camera via HTTPS tunnel | Not yet tested |
| Coordinator display | MacBook browser, wired Ethernet to the Pi | Verified link |
| Stretch: airborne drone | One of the reviewed models, if an aircraft + operator are confirmed | Unconfirmed |
| Stretch: physical MOB button | Seeeduino + Grove button | Board verified, no sensors attached |
| Stretch: ESP-NOW telemetry | 2× XIAO ESP32-C5 | Blocked on a USB data cable |

Venue Wi-Fi isolates clients and is the Pi's internet uplink. Scouts therefore push to the Pi through a Cloudflare quick tunnel (outbound connections only), which also gives the phone the HTTPS it needs for camera access. Internet is available (accepted).

## Mission flow

1. **Standby.** Ship camera watches a marked rail line. Display shows "Deck watch active".
2. **Automatic MOB.** A tracked person on the ship camera crosses beyond the rail line (depth beyond a configurable rail distance, held for N frames, or lost from view immediately after approaching it). The system opens one incident, stores the ship-camera screen grab and the overboard point, and starts candidate detection on both scouts. A manual MOB control remains as fallback.
3. **Search.** No scout sighting yet: show the drift estimate growing from the overboard point.
4. **Confirm.** First scout candidate requires coordinator confirmation. Confirmation starts tracking and following (Scout A pan-tilt; drone if available; Scout B is human-held).
5. **Track.** Retained screen grab and location update automatically per scout. Second scout associates automatically within 50 m of the most recent accepted location.
6. **Coordinator-link outage (5 s).** Pull the Mac's Ethernet cable (or use the demo toggle). Ground processing, retention and following continue. Display shows LINK LOST, last received evidence and advancing age.
7. **Recovery.** Current state and live video first (≤ 3 s target), then timestamped backlog. Older data never overwrites newer.
8. **Visual loss.** Hide the person from both scouts. After both sightings are older than 6 real seconds, the drift estimate grows from the latest accepted sighting on an accelerated, labeled scenario clock.
9. **Reacquire.** ≤ 50 m from that node's last location before loss: resume automatically. > 50 m or unreliable location: show candidate, keep prior sighting, require confirmation.
10. **End Incident.** Stop tracking/following, preserve history; late messages cannot reopen it.

## Coordinates and honesty labels

- The ship has a configured pose in Massachusetts Bay. The ship camera's depth gives a **real** person position relative to the ship (venue scale). It is placed on the chart through the ship pose; label "real relative geometry, simulated ship position".
- Scouts have no real geolocation. Their person locations come from a simulated scenario truth (seeded at the overboard point, drifting under different parameters than the estimator) plus noise. Label "simulated coordinates". The hidden truth never feeds the estimator.
- Every location carries provenance (`real_relative`, `simulated`, `none`) and quality. Missing/unreliable locations force coordinator confirmation.
- Drift area is labeled ESTIMATE with model name, data source/time/location, simulated elapsed time and speed multiplier.
- TurboPi following is labeled "ground stand-in"; any pilot-flown behavior is labeled "pilot assisted".

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | Ship-camera rail crossing opens exactly one incident and starts candidate detection on both scouts; manual MOB does the same |
| FR-02 | Observations carry incident, node, source session, sequence, capture time, association, image reference, location + provenance + quality |
| FR-03 | Ground processor retains observations through a coordinator-link outage |
| FR-04 | Each node shows last valid screen grab, location and advancing age through every loss state |
| FR-05 | Distinguish visual contact lost, video input lost, and coordinator link lost |
| FR-06 | Drift estimate shown from the overboard point before first contact and whenever no sighting is fresh, with environmental provenance |
| FR-07 | On recovery, newest state and video first, then backlog |
| FR-08 | Duplicate, reordered or restarted-source messages cannot rewind state or reopen/recreate an incident |
| FR-09 | Inclusive 50 m association/reacquisition rules with confirmation fallback |
| FR-10 | Outage injection affects only the processor→display path (no read-through) |
| FR-11 | Confirmation starts tracking/following; Stop/override always available |
| FR-12 | Ship camera and both scout feeds visible together, each falling back to retained evidence |
| FR-13 | Scout A follows (keeps person in central image region), holds on visual loss |
| FR-14 | End Incident stops activity, preserves history |

Thermal is dropped from scope (no device in hand).

## Targets (provisional, record actuals)

| Measure | Target |
|---|---|
| MOB trigger | ≤ 2 s from rail crossing to MOB banner |
| Acquisition | ≤ 5 s from person clearly visible to scout candidate on display |
| Live video | ≥ 10 displayed fps per feed, all feeds together |
| Video latency | ≤ 1 s capture to display (tunnel adds latency; measure) |
| Freshness | Stale when capture age > 6.0 real s (exactly 6.0 is fresh) |
| Outage / recovery | 5 s outage; ≤ 3 s to current state after link returns |
| Association radius | ≤ 50 m inclusive |

## Out of scope

Real ocean detection performance, autonomous takeoff/search, ship maneuvering, spoken directions, video replay, thermal, calibrated probability claims for the drift area.
