# Osprey — man-overboard response under degraded comms

Team 29, CodeMetal Forge 2026.

A ship's deck camera sees someone go over the rail and declares **man overboard** automatically. Two scout nodes (stand-ins for drones) search, the coordinator confirms the person, and the scouts lock on and follow. When comms drop or the person slips out of view, the coordinator's picture degrades honestly: last evidence with a ticking age, then a drift-driven search area. When contact returns, the picture recovers without stale data overwriting fresh data.

| | |
|---|---|
| Ship deck camera | Deptrum Aurora 930 RGB-D: rail-crossing trigger and real relative position |
| Ground processor | Raspberry Pi 5 + Hailo-8 person detection |
| Scout A | Hiwonder TurboPi rover with a pan-tilt camera that follows the person (ground stand-in for a drone) |
| Scout B | Phone camera through an HTTPS tunnel (proxy for a second drone) |
| Coordinator | Browser display on a laptop, wired to the ground processor |

## Docs

- [PRD](docs/prd.md): story, requirements, targets, honesty labels
- [Implementation plan](docs/implementation-plan.md): architecture, contracts, phases
- [Hardware state](docs/hardware.md): what has been verified
- [Hardware setup](docs/hardware-setup.md): bring-up steps for the team
- [Research](docs/research.md) · [Event constraints](docs/event-constraints.md)

## Status

Hardware verified Nov 7: Pi 5, Hailo-8, and the Aurora 930 streaming RGB/IR/depth. Software is in progress; run commands will be added here as they work.

## Licensing

Apache-2.0. Third-party SDKs, models and data keep their own licenses: the Deptrum SDK is not redistributed here, and Hailo models are installed from Raspberry Pi OS packages.
