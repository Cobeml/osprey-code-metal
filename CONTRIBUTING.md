# Team workflow

## Coordinate before implementation

The [PRD](docs/product/prd.md) holds the current product requirements and decision status. Meeting notes record discussion. Engineering documents hold the implementation baseline, design recommendations and hardware gates. A change in one should update the affected others in the same commit.

Core scope is consolidated. One person uses Claude or Codex for implementation and integration. Record that owner and the flight operator before hardware testing. Resolve material scope changes with the user and record accepted decisions in the PRD.

## Development workflow

1. Fetch current main and create a short-lived feature branch.
2. State the requirement IDs and acceptance case addressed by the change.
3. Agree on the interface with the component receiving your output.
4. Make a small end-to-end increment and run the relevant checks.
5. Open a pull request with behavior, evidence, assumptions and known failures.
6. Integrate regularly and rehearse from a clean checkout.

Keep execution reproducible. For the accepted Python/backend and browser/display stack, commit the dependency manifest and lockfile, document exact setup/run/test commands here, and add CI for checks that actually run. Capture the Python/runtime, OS, CPU architecture, accelerator firmware/runtime and model version used in a hardware result.

## Boundaries and data

Keep capture/device drivers and transport adapters outside the estimation logic. Exercise core logic with deterministic fixtures. Preserve observation timestamps through every adapter. Source restart, duplicate delivery and reconnect behavior belong in integration tests.

Small synthetic fixtures may be committed with provenance. Keep model weights, recordings, secrets and runtime databases outside Git by default. Record upstream URLs, versions and licenses for downloaded assets.

Automated coding output requires review and execution against the stated acceptance case. Document the code and artifacts that predate the event separately from work built during the event.

## Current execution state

Runtime code and executable tests are pending. Adding empty CI or untested installation instructions would give the team no verification evidence. The first implementation change should supply a minimal runnable producer-to-receiver path, its setup commands and one repeatable acceptance case.
