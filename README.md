# Team 29 — Open-ocean man-overboard response

Help a search-and-rescue coordinator direct the ship using evidence about a person in the water through intermittent drone observations and communications.

**Status — core scope consolidated, November 7, 2026.** The PRD records the accepted interview decisions, provisional performance targets and hardware gates. Runtime implementation, integration and measured results are pending.

## Start here

1. [PRD](docs/product/prd.md) — accepted scope, requirements, decision register and remaining hardware gates.
2. [System architecture](docs/engineering/architecture.md) — edge processing, communications and operator responsibilities.
3. [Hardware and integrations](docs/engineering/hardware.md) — promised equipment, checkout dependencies and interface checks.
4. [Software and public repositories](docs/engineering/software.md) — reusable components and selection constraints.
5. [Verification and demo](docs/engineering/verification.md) — measurable acceptance cases.
6. [Research](docs/research/man-overboard.md) — existing systems, physical constraints and supporting evidence.
7. [Meeting notes](docs/meetings/README.md) — the two Granola discussions informing this project.
8. [Team contribution workflow](CONTRIBUTING.md) — how to develop and integrate work.

## Repository layout

```text
docs/
  product/       PRD and project constraints
  engineering/   Architecture, interfaces, hardware, software, verification
  research/      Cited evidence and limitations
  meetings/      Dated discussion records
src/             Runtime implementation
tests/           Automated verification
fixtures/        Small, labeled reproducible scenario inputs
CONTRIBUTING.md   Team workflow and implementation gates
LICENSE          Apache-2.0 repository license
```

Use one repository and a small number of processes. Create implementation modules as their responsibilities become concrete. Runtime code belongs in src, repeatable checks in tests, and test inputs in fixtures. Use the accepted Python backend and browser display stack. One person uses Claude or Codex for implementation and integration. Select device adapters after checkout and follow the build sequence in the software document.

## Accepted demo

MOB declaration starts candidate detection on two live sensor nodes. The coordinator confirms one person, then tracking and following begin. One node is an airborne drone and the other a live camera proxy for a second drone. Use autonomous fixed-camera following where supported and label pilot assistance otherwise.

Process video on the ground. Show both feeds and independent per-node state. Retain screen grabs, person locations and observation age through visual loss or coordinator-link loss. Use the inclusive 50 m association rules in the PRD.

Demonstrate a five-second processor-to-display outage with a provisional three-second recovery target. Separately hide the person and show a labeled accelerated ocean drift simulation after both sightings exceed six real seconds in age. Preloaded wind/current data and clearly labeled simulated person coordinates are accepted. Live detection takes place at the venue.

Read the [ordered build sequence](docs/engineering/software.md#ordered-build-sequence) and [acceptance checklist](docs/engineering/verification.md#acceptance-checklist). The organizer cutoff is **November 8, 2026 at noon EST**. See [event constraints](docs/product/event-constraints.md).

## Evidence and licensing

Label live detections, simulated coordinates, drift estimates and pilot assistance explicitly. The accepted demonstration uses live video. Source availability does not establish device compatibility or field performance. Third-party code, model weights and datasets retain their own licenses. Record chosen versions and terms before incorporating them.
