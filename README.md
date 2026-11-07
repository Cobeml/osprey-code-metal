# Team 29 — Open-ocean man-overboard response

Help a ship and rescue boat maintain a useful picture of a person in the water through intermittent drone observations and communications.

**Status — requirements discovery, November 7, 2026.** This repository contains the team's current planning foundation. Application code, hardware integration and measured performance are pending. The PRD interview continues one question at a time.

## Start here

1. [Draft PRD](docs/product/prd.md) — problem, scope, proposed requirements and unresolved decisions.
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

Use one repository and a small number of processes. Create implementation modules as their responsibilities become concrete. Runtime code belongs in src, repeatable checks in tests, and test inputs in fixtures. Source packages, execution commands and CI will be selected with the implementation stack.

## Scenario and current proposal

A crew member declares man overboard in open ocean. A camera node acquires a candidate, tracks observations and reports evidence to the ship. The operator view distinguishes a fresh sighting, reported visual loss, and a stale communications link. It preserves the last observation and presents a separately identified estimate when evidence ages.

The manual trigger and maritime mission come from the team discussions. One drone, three-second updates, live-versus-replay scope, GNSS assumptions and the primary operator remain proposed or unresolved. Consult the PRD before treating these as requirements.

The organizer briefing records **November 8, 2026 at noon EST** as the submission cutoff. See [event constraints](docs/product/event-constraints.md).

## Evidence and licensing

Label each result as live hardware, replay or simulation. Source availability does not establish device compatibility or field performance. Third-party code, model weights and datasets retain their own licenses. Record chosen versions and terms before incorporating them.
