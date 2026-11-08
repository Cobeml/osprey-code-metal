# Mission theatre — revision 6

Built on upstream snapshot `5d7881076daad57e85de040681ae287ba68f8d32`. This feature is separate from the operational coordinator in `web/`.

From the repository root:

```bash
python3 -m http.server 8087 --bind 127.0.0.1 --directory simulation
```

Open **http://127.0.0.1:8087/**. No package installation or Pi connection is needed to play the bundled simulation. Use HTTP rather than opening `index.html` as a file, because the browser loads a JSON fixture.

To regenerate the fixture after installing the repository's development dependencies:

```bash
.venv/bin/python simulation/tools/build_story.py
.venv/bin/pytest tests/test_mission_simulation.py -q
```

 Press Play once. Six amber in-scene explainers hold for three seconds and advance automatically. Pause freezes their countdown; Reset re-arms them.

## Story

- 2–3 s: person falls overboard.
- 3 s onward: accelerated drift rapidly separates the person from the vessel. The ship continues forward.
- 5 s: five UAVs and the USV launch together. Aircraft fan out to five separate, drift-following back-and-forth lane groups offshore. Scanning starts only after reaching the grid and beyond an 80-scene-meter exclusion around the ship. The USV performs a slow rectangular sweep near the launch point.
- 32 s: scripted positive lock. Drones converge into a compact observation formation; the displayed uncertainty region contracts over three seconds. The USV changes from 0.75 to 16 scene meters per story second, creating a visible intercept. The ship starts a gradual turn back.
- 36 s onward: uninterrupted observation and a distance-to-confirmed-fix readout show the gap closing.
- 49 s in the current deterministic fixture: USV reaches within approximately four meters of the observed person and the simulation stops. No loss-of-contact or reacquisition sequence, and no physical recovery animation.

The story lasts approximately 67 seconds at 1× including six automatic cards, excluding pauses and rendering slowdowns. The overview camera fits the dispersed search, then closes in on the rendezvous. Ship and vehicle models are illustrative, not scale-certified. The five-drone swarm represents the product vision; the physical prototype remains a piloted Aquila16 and TurboPi rover.

## Model and layout

`simulation/tools/build_story.py` reuses Osprey's `LeewayEnsemble`, 800 PIW-1 estimate particles and the archived Massachusetts Bay Open-Meteo snapshot. Separate PIW-2 scenario truth and random draws supply scripted noisy observations only after lock. Search planning never reads hidden truth.

Before lock, one story second advances 60 model seconds; after lock it advances six, so the final approach remains legible. These are cinematic time-compression settings, not measured drift rates or response times. The UI labels compressed scenario time and shows the actual model clock.

The aerial planner compares 36 candidates: four orientations relative to predicted target drift (0°, −30°, +30°, 90°), three lane spacings (20, 30, 40 m), and three longitudinal offsets (−40, 0, 40 m). Each assigns two lanes to each of five UAVs. The launch grid is constructed from a six-story-second-ahead particle forecast; its offshore exclusion is a demo constraint. Its origin then translates with the predicted ensemble median while shape/orientation remain fixed. This prevents noisy replanning while following the drifting search area. Every frame retains the moving grid and continuous aircraft positions.

Each candidate is simulated over the same 27-story-second pre-lock horizon using 800 predicted particle trajectories. The score is mean cumulative detection proxy, so earlier detections count more. It uses an ASSUMED Gaussian cross-track sensor function (12 m sigma, peak 0.65 per one-second step), finite 18-scene-m/s vehicle motion, transit before scanning, relative swept-segment distances and cumulative missed detections. Repeated observations are assumed conditionally independent. The selected candidate maximizes this score within the finite candidate set. Selection and all candidate scores are saved in `mission-drift.json` under `planning`.

This is not a global optimum, SAROPS implementation, calibrated detection model, flight-dynamics solver or demonstrated rescue probability. It ignores turn-rate/battery constraints and correlated misses. Candidate scoring uses only the predictive ensemble, never scenario truth. Actual story lock remains scripted. The UI probability footprint is not reweighted from negative searches. The USV keeps the user's near-launch slow allocation; its small box is rotated into the water-current direction and is not jointly optimized with the UAVs. See [RESEARCH.md](RESEARCH.md) for sources and design reasoning.

The estimate resets with assumed 2 m observation uncertainty. Its central 50% and 90% hulls are model ensemble regions, not calibrated real-world coverage or rescue-success probabilities. Display easing resamples the hulls to 96 angular vertices and interpolates the pre/post-fix boundary over three seconds; the area readout interpolates endpoint model areas. This visual transition is not measured sensor latency.

## Standalone runtime and validation

Serve only this directory with Python's static file server. The browser loads local JavaScript, styles, Three.js and the baked JSON fixture. There are no coordinator API calls, WebSocket connections, embedded coordinator or hardware controls. The operational coordinator stays in `web/`, served by the existing Osprey application.

Three.js 0.170.0 is vendored with its MIT license. Geometry, ocean normals and reflection environment are procedural; no graphics CDN or art service is required. Model generation optionally reuses `osprey.drift` from the repository, but the baked simulation runs without Osprey, NumPy, hardware or an installed project environment.

Validation includes the repository suite, translating-grid and best-candidate selection tests, three-second playback checks, standalone browser rendering, and a check that simulation code cannot call coordinator endpoints. Physical hardware and maritime performance are not validated by this concept demo.
