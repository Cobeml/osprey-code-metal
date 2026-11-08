# Implementation plan — for the Claude Code implementation session

Read first: [PRD](prd.md) (what and why), [hardware.md](hardware.md) (verified facts), [hardware-setup.md](hardware-setup.md) (what the human is doing in parallel). Deadline: **Nov 8, 12:00 EST**. Push to `origin/main` only when the user approves; remind them well before noon.

## Principles

- **Always demoable.** After Phase 2 a fully simulated demo runs end to end. Each later phase swaps a simulated piece for real hardware behind the same interface, with the simulation kept as fallback (config switch).
- **Hardware-free work first.** Phases 0–2 and 6 need no new hardware. Hardware phases wait on the human's checkpoints. Never block: if a checkpoint isn't ready, take the next hardware-free phase.
- **Small, boring stack.** One Python process on the Pi (FastAPI + asyncio), plain HTML/JS/CSS UI with Leaflet from a CDN, no frontend build step, SQLite, one small C++ bridge for the Aurora.
- **Honest labels everywhere** (see PRD "Coordinates and honesty labels").
- Commit after each working increment, with requirement IDs in the message. Tick the phase checkboxes in this file as you go.

## Coordination with the human (concurrent hardware setup)

- Ask before: rebooting the Pi, installing system packages, downloading anything new (state name, source, size), or touching the TurboPi.
- Never ask the user for passwords; they run `ssh-copy-id` themselves.
- Checkpoints from [hardware-setup.md](hardware-setup.md): H1 (Aurora mounted), H2 (phone ready), H3 (TurboPi reachable). When one arrives, finish the current small task, then verify it.
- Pi access: `ssh mob-pi`. Code lives in this repo on the Mac and deploys to `~/osprey` on the Pi with `scripts/deploy.sh` (rsync). Don't edit code directly on the Pi.

## Architecture

```text
 Ship cam (Aurora, USB) ── native/aurora_bridge (C++) ─stdout─┐
 Scout A (TurboPi) ──WSS via Cloudflare tunnel──┐              │
 Scout B (phone /scout page) ──WSS via tunnel───┤              ▼
                                                └──► osprey (FastAPI on Pi 5)
                                                       ├ ingest: per-node frames + capture timestamps
                                                       ├ perception: Hailo-8 yolov8s person detector + IoU tracker
                                                       ├ shipcam: rail-crossing MOB trigger, depth → ship-frame XYZ
                                                       ├ incident: state machine, 50 m rules, freshness, retained evidence
                                                       ├ scenario: ship pose, sim person truth, scout sim coordinates
                                                       ├ drift: Monte Carlo leeway + accelerated scenario clock
                                                       ├ follow: commands to Scout A (pan-tilt)
                                                       ├ store: SQLite append-only events (ground retention)
                                                       └ gateway: coordinator WS (+ outage injector) ──Ethernet──► Mac browser UI
```

The coordinator UI holds its own snapshot and ages it locally. It never reads ground state except through the gateway (FR-10). Pulling the Mac's Ethernet cable is the real outage; the demo drawer has a 5 s software outage as backup.

## Repo layout (target)

```text
pyproject.toml            deps + pytest config (Python 3.13 on Pi; match on Mac with uv or venv)
src/osprey/
  app.py                  FastAPI app, routes, startup wiring
  config.py               settings (yaml + env), sim/real switches per node
  contracts.py            pydantic models: Frame, Detection, Observation, NodeState, Incident, Command, Ack, events
  clock.py                real clock, per-source offset estimation, scenario clock (multiplier, anchor)
  geo.py                  ENU <-> lat/lon, ship pose, horizontal distance
  store.py                SQLite event log, idempotent by event_id, per-session sequence
  incident.py             phases, confirm, association/reacquisition, freshness, end (pure logic, no IO)
  perception/detector.py  Hailo yolov8s_h8 wrapper (+ SimDetector)
  perception/tracker.py   IoU tracker with track ids
  shipcam.py              rail-crossing trigger, depth sampling, ship-frame position
  nodes/aurora.py         spawn + parse aurora_bridge output (RGB JPEG + depth)
  nodes/ws_ingest.py      scout WebSocket ingest (binary frames), clock offset pings
  nodes/sim.py            synthetic frames/detections for dev, tests and fallback
  scenario.py             sim person truth (separate params from estimator), scout coordinates
  drift.py                leeway Monte Carlo, hulls, seeding policy
  follow.py               Scout A follow/hold/stop command generation
  gateway.py              coordinator WS: snapshot, deltas, heartbeat, history replay, outage injector
web/
  index.html, app.js, style.css   coordinator display
  scout.html, scout.js            phone capture page
native/aurora/            aurora_probe.cc (verified), aurora_bridge.cc, build.sh
turbopi/scout_client.py   runs on the TurboPi: camera -> WS, follow commands -> servos
scripts/                  deploy.sh, run_pi.sh, tunnel.sh, check_hardware.py, fetch_env.py, measure_latency.py
fixtures/env/             Open-Meteo snapshot JSON + provenance
tests/                    pytest
docs/                     prd, hardware, hardware-setup, this plan, results.md (measured evidence)
```

## Key contracts and rules

**Scout frame message** (binary WebSocket): `uint32 header_len | header JSON | JPEG`. Header: `node_id, session_id, seq, capture_ts_ms (sender clock), width, height`. The server answers periodic `{"ping": t}` messages so it can estimate each sender's clock offset. It records `clock_quality` (`synced` / `estimated` / `unknown`).

**Observation** (FR-02): `event_id, incident_id, node_id, session_id, seq, capture_ts (server clock domain), received_ts, kind (candidate|accepted|lost|input_lost), track_id, target_id, bbox, confidence, image_ref, location {lat, lon, provenance: real_relative|simulated|none, quality: good|degraded|unreliable, accuracy_m}`.

**Freshness:** `stale = (now - capture_ts) > 6.0` s in real time. Exactly 6.0 is fresh. Heartbeats, duplicate delivery and late delivery never refresh it.

**Ordering (FR-08):** dedupe by `event_id`. Within a session, ignore `seq <=` the last applied seq for state updates (still archive to history). A new `session_id` from a node is accepted as a restart; it never resurrects a closed incident. Current state only moves forward by `capture_ts`.

**Association (FR-09), horizontal distance in meters, inclusive:**

| Case | Reference point | ≤ 50.0 m | > 50 m, or missing/unreliable location |
|---|---|---|---|
| First candidate of the incident | — | coordinator confirms | coordinator confirms |
| Second node, first association | most recent accepted location (any node) | auto-associate | candidate + confirm |
| Reacquisition after this node's visual loss | this node's last accepted location before loss | auto-resume | candidate + confirm, keep prior sighting |

Multiple simultaneous candidates: the highest-confidence feasible one auto-associates; the others are shown as candidates. Document this in code.

**Phases (UI banner):** `STANDBY → OVERBOARD (search) → CANDIDATE → TRACKING → CONTACT LOST (drift) → TRACKING … → ENDED`. `LINK LOST` is an overlay computed by the browser, not a backend phase.

**Ship-cam MOB trigger (FR-01):** the person is tracked on the ship cam, with depth `Z` = median of the valid depth in the inner 50% of the box. Arm when `Z < rail_m`. Trigger when, after arming, `Z > rail_m + hysteresis` for ≥ 3 consecutive frames, **or** the track is lost within 1.5 s of `Z > rail_m - 0.3`. Exactly one incident per arming; re-arm only after End Incident. Overboard point = ship pose ⊕ camera-frame (X, Z), using intrinsics from the bridge. Label `real_relative`. Store the trigger frame as evidence.

**Drift (FR-06):** N≈1000–2000 particles in local ENU. Velocity = current + leeway(wind) for a person in water, plus random-walk diffusion. Use published PIW leeway coefficients (Allen & Plourde 1999 / Breivik et al. 2011): **look up the actual downwind/crosswind slope and offset values and cite them in code**; don't invent numbers. Forcing comes from an Open-Meteo snapshot for Massachusetts Bay (marine API for ocean current velocity/direction, forecast API for 10 m wind; verify variable names), fetched by `scripts/fetch_env.py`, committed under `fixtures/env/` with URL, time and coordinates. Seed from the overboard point at MOB, and from the latest accepted sighting when contact is lost. Suspend while any sighting is fresh. The scenario clock multiplier (default 60×) affects only drift integration. Render 50% and 90% particle hulls labeled ESTIMATE with model, data source, simulated elapsed time and multiplier. The scenario truth uses different coefficients and its own noise, and never feeds the estimator.

**Gateway:** heartbeat every 500 ms with server time. The browser shows LINK LOST after 1.5 s without a message. On (re)connect it sends a snapshot (incident, per-node state, latest frame per node) immediately, then history in capture-time order, flagged `history: true`. The browser applies history to the timeline only and never lets it overwrite newer current state (FR-07). Live JPEG frames are relayed as binary messages tagged by node (latest-only, drop when the socket is slow). Commands carry `command_id` and are idempotent. Every command gets an ack; the UI only shows success after the ack arrives.

## Coordinator UI (keep it simple, tell the story)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  ● MAN OVERBOARD — searching             incident 00:42        [LINK OK]       │  ← one big phase banner
├───────────────────────────────────────────────┬──────────────────────────────┤
│                                               │ SHIP DECK CAM   ● LIVE        │
│   Chart (Leaflet)                             │ [video] rail line overlay     │
│   🚢 ship   ✕ overboard point                  ├──────────────────────────────┤
│   ◉ A last sighting (age 3.1 s)               │ SCOUT A (rover) ● TRACKING    │
│   ◉ B last sighting (age 7.9 s, stale)        │ [video] box on person         │
│   ░░ ESTIMATE 50%/90% — Leeway MC,            ├──────────────────────────────┤
│      Open-Meteo 2026-11-07 Mass Bay,          │ SCOUT B (phone) ○ CONTACT LOST│
│      sim +14 min @60×                         │ [last grab] seen 7.9 s ago    │
├───────────────────────────────────────────────┴──────────────────────────────┤
│  [ CONFIRM PERSON ]  [ STOP FOLLOWING ]  [ END INCIDENT ]          (D = demo)  │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Banner colors: standby grey, overboard red, tracking green, contact lost amber, ended blue. A banner subtitle explains the phase in one plain sentence ("Deck camera saw a person cross the rail at 15:42:07").
- Each feed tile has one state pill: `LIVE` / `CANDIDATE` / `TRACKING` / `CONTACT LOST` / `NO VIDEO`. When video is missing or stale, show the retained screen grab with "last seen X s ago", where the age ticks locally.
- LINK LOST: dim the whole screen slightly, show a red "Link to ground processor lost — showing last received data" ribbon, and keep the ages ticking.
- CONFIRM only appears when a candidate needs a decision. Clicking a candidate box or marker selects it.
- A small timeline strip at the bottom is optional (MOB, confirm, lost, reacquired, history-arrived markers).
- The demo drawer (key `D`) is hidden by default: manual MOB, 5 s outage, sim speed, inject scout candidate at 30 m / 80 m, toggle a node's sim/real source.

## Phases

Rough budget ≈ 15 h of build plus rehearsal. Hardware dependency in brackets.

### Phase 0 — Bootstrap (30 min) [none]
- [ ] `pyproject.toml` (fastapi, uvicorn[standard], pydantic, pyyaml, numpy, pytest, httpx, websockets). Mac venv with `python3 -m venv .venv`. Pi venv at `~/osprey/.venv` created with `--system-site-packages` (keeps `hailo_platform`, `cv2`).
- [ ] `scripts/deploy.sh`: rsync the repo (excluding `.venv`, `.git`, `hardware-checks`) to `mob-pi:~/osprey`, then `pip install -e .` in the Pi venv.
- [ ] `scripts/run_pi.sh`: runs uvicorn on `0.0.0.0:8000` under `nohup` or `systemd --user`, logging to `~/osprey/runtime/`.
- [ ] `scripts/check_hardware.py`: Hailo identify, Aurora present (USB 3251:1930), serial ports, camera open via probe, prints a pass/fail table.
- [ ] Remove the obsolete `~/mob-sar` on the Pi (contains only the probe build).
- [x] Ask the user, then install `cloudflared` (arm64 .deb from Cloudflare's GitHub releases) on the Pi; `scripts/tunnel.sh` starts a quick tunnel and prints the URL.
- Done when: `pytest` runs on the Mac (0 tests OK), deploy works, `http://169.254.50.2:8000/health` answers from the Mac.

### Phase 1 — Core domain, test-first (2 h) [none]
- [x] `contracts.py`, `clock.py` (injectable fake clock), `geo.py`, `store.py`, `incident.py`.
- [x] Tests: freshness 6.0 fresh / 6.001 stale; 49.9 / 50.0 / 50.1 m for both reference rules; missing/unreliable location → confirm; duplicates, reordering, old-session packets, restarted session; End Incident is final (late events go to history, retried end is idempotent); confirm idempotent by command_id; multiple candidates.
- Done when: all tests green. Covers FR-02/04/05/08/09/11/14 logic.

### Phase 2 — Simulated end-to-end + UI v1 (2.5 h) [none]
- [x] `nodes/sim.py`: three sim nodes producing synthetic JPEGs (moving person rectangle on a sea-colored background, labeled SIM) at 10 fps, plus a scripted ship-cam rail crossing.
- [x] `scenario.py` with ship pose (default ≈ 42.35 N, −70.80 W, heading configurable) and sim truth.
- [x] `gateway.py`, `app.py` routes, `web/` coordinator UI per the sketch, demo drawer.
- [x] Run locally on the Mac, then deploy to the Pi and open `http://169.254.50.2:8000` on the Mac.
- Done when: a fully simulated story plays: auto MOB → search area → candidate → confirm → tracking → hide → drift grows → reacquire → end. Commit, and tell the user "sim demo works" (this is the safety net).

### Phase 3 — Ship deck camera, real (2 h) [Aurora connected; H1 for calibration]
- [x] `native/aurora/aurora_bridge.cc`, based on `aurora_probe.cc` (mode 2, 640×400, ~14 fps, aligned, heartbeat on). Each frame goes to stdout as a length-prefixed header JSON + RGB JPEG + depth uint16 (PNG or raw). Recover from device errors by exiting non-zero; Python restarts it.
- [x] `perception/detector.py`: Hailo `yolov8s_h8.hef` via `hailo_platform` (check output format with `hailortcli parse-hef`; the model has on-chip NMS). One shared VDevice for all nodes. Benchmark fps.
- [x] `perception/tracker.py`, `shipcam.py` trigger and geometry; the rail line drawn on the ship-cam video.
- [ ] With H1: the user stands on the tape, set `rail_m` from measured depth, walk across, and confirm one MOB per crossing.
- Done when: walking past the tape on the real camera opens the incident within 2 s, with the trigger frame and overboard point shown. Record trigger latency in `docs/results.md`.

### Phase 4 — Phone scout via tunnel (1.5 h) [H2]
- [x] `web/scout.html`: choose node (A/B), `getUserMedia` (rear camera, 640×480), canvas → JPEG q≈0.7 at 10 fps → WSS, clock pings, on-screen status.
- [x] `nodes/ws_ingest.py` with bounded latest-frame queues; scouts run through the detector.
- [ ] `scripts/measure_latency.py` or an on-screen timestamp method; record fps and latency.
- Done when: the phone feed shows live boxes on the coordinator at ≥ 10 fps and its latency is recorded.

### Phase 5 — Outage and recovery (1 h) [none; cable-pull test needs the user present]
- [x] Browser local aging, LINK LOST overlay, reconnect snapshot-then-history, software outage toggle.
- [ ] Test: pull the Mac Ethernet for 5 s during tracking. Ground keeps tracking and archiving, the display recovers in ≤ 3 s, and history fills the gap without rewinding.
- Done when: V-02/V-05 behavior has been shown live and timing is recorded.

### Phase 6 — Drift with real forcing (1.5 h) [none]
- [x] `scripts/fetch_env.py` → `fixtures/env/massbay-*.json` (ask before the first network fetch; it's tiny).
- [x] `drift.py` + tests: clock independence (changing the multiplier doesn't change freshness/outage timing), seeding policy, area grows monotonically while unseeded.
- [x] UI hulls and labels.

### Phase 7 — TurboPi Scout A (2–3 h) [H3]
- [ ] Inspect the TurboPi OS and Hiwonder SDK (servo control call, camera device). Don't modify vendor files.
- [ ] `turbopi/scout_client.py`: capture → same binary WS protocol through the tunnel. Receive `follow {bbox_center_err}` / `hold` / `stop`. A local P/PI loop on the pan-tilt servos keeps the person in the central region (±15% of frame), with rate limits. It holds position when commands go stale for > 1 s (visual loss or link loss).
- [ ] `follow.py` on the Pi: send follow errors only when the incident is TRACKING and Scout A has the confirmed target; stop/override takes priority.
- Done when: the rover's camera visibly follows a walking person after confirm, stops on STOP, and holds when the person hides.

### Phase 8 — Rehearsal and evidence (1.5 h) [all]
- [ ] `docs/demo-script.md`: 3-minute run order matching the PRD story, with who does what.
- [ ] `docs/results.md`: measured trigger latency, acquisition time, fps per feed, latency, outage recovery, with device and software versions.
- [ ] README quickstart (exact commands). A clean-checkout rehearsal from the Mac. Ask the user to push.

### Phase 9 — Rover over Wi-Fi (Nov 8) [user: Wi-Fi credentials typed on the rover]
- [x] Rover autonomy on link loss: camera, lock, search and approach run on the rover whatever the link does; the rover stops by itself after `--autonomy-s` (60 s) without the ground, since a coordinator stop cannot reach it then. Verified on the rover with `--hw none` against a fake ground (link drop, carry on, cap, reconnect).
- [x] URL failover: `ROVER_URLS` wired first, then the Cloudflare tunnel (`deploy_rover.sh urls`); `--fps` / `--jpeg-q` for a thin link.
- [x] `turbopi/osprey-rover.service` + `deploy_rover.sh autostart on|off` (on disables Hiwonder's `start_node`, which holds the motors and camera). Not enabled yet: needs the user's OK.
- [ ] Rover wlan0 from its own hotspot (`hiwonder-ap`) to a network with internet (venue Wi-Fi, phone hotspot or a travel router); the user types the password.
- [ ] Test: unplug the rover's Ethernet mid-incident; it fails over to the tunnel within a few seconds and keeps going. Measure video fps and command latency over the tunnel.
- Risk: the quick-tunnel URL changes when cloudflared restarts (Pi reboots). Re-run `deploy_rover.sh urls` over the cable, or use a named tunnel / travel router (stable address).

### Phase 10 — UWB range beacon on the ball (next) [2× Qorvo DWM3001CDK]
Real MOB beacons are worn by the person, so: one board on the ball ("the person's beacon"), one on the rover (USB to the rover Pi). UWB two-way ranging gives distance only (~10 cm, tens of Hz, no angle: one antenna each). The rover's camera already gives the angle, so camera + range = a real 2D fix; range alone still helps when the ball is out of view.
- [ ] Identify the firmware: plug a board into the Mac, read the banner on `/dev/cu.usbmodem*` at 115200. Qorvo's CLI firmware ranges with `INITF` (rover, initiator) / `RESPF` (ball, responder). If it ships with the Nearby Interaction demo instead, reflashing needs J-Link / nRF tools (ask before installing).
- [ ] Ball side: board + small USB power bank, `RESPF` at power-up (saved config if the firmware allows, else a boot script on a tiny host).
- [x] Rover side: `turbopi/uwb.py` reads ranges from `/dev/ttyACM*` in a thread (median of the last 5, stale after 0.6 s, raw termios, no pyserial). Parser takes Qorvo CLI JSON (`D_cm`) and key/value text; tested incl. a pseudo-terminal. `turbopi/uwb_probe.py` shows raw output + parsed ranges. Still to do: check the parser against the real board's lines.
- [x] Use it in `scout_client.py` behind `--uwb` (off by default, today's behaviour unchanged). Unit-tested, not yet driven:
  - run-out distance = UWB range instead of the 1.5 m default;
  - arrival = range ≤ 0.4 m (with the box as a cross-check);
  - (not done) lock check: a green blob whose box-size distance disagrees with UWB range by > 50 % is a decoy;
  - lost from view: drive short legs and keep the heading that makes the range shrink (gradient search), then camera sweep as now.
- [x] Rover reports `uwb_m` every second; the Rover tile shows "UWB 1.23 m to beacon · MEASURED" (checked locally with a fake rover). Range ring on the chart not done: the rover's chart position is simulated.
- [ ] Later: board with the phone operator for phone↔rover range (triangulation with the phone's bearing to the ball).

### Stretch (only after Phase 8 rehearses cleanly)
- S1 Grove button on D2 → `/api/commands manual_mob` via a small Seeeduino sketch (`arduino-cli` on the Pi) and a serial reader.
- S2 ESP-NOW mirror of compact observations between the two XIAO ESP32-C5s (≤ 250 B packets), shown as a "radio link" status. Needs a data cable.
- S3 Drone as Scout A' if an aircraft and operator appear; FPV capture via a USB grabber into the same ingest path; label "pilot assisted".

## Fallbacks

| Risk | Fallback |
|---|---|
| Hailo Python API fights back | Run Hailo's packaged detection example to validate first; temporary CPU detector (OpenCV HOG person) to keep the pipeline moving |
| Tunnel slow or blocked | Scouts on the wired switch (static 169.254.50.x) or the Pi as a Wi-Fi hotspot (loses the Pi's internet; use only at demo time) |
| TurboPi SDK unclear | Treat the rover as a fixed scout (video only); label following as not demonstrated |
| Aurora depth unreliable at venue | Trigger on the box crossing the rail line in the image (manually calibrated), labeled degraded |
| Anything at demo time | Config switch back to the Phase 2 sim node for that feed, clearly labeled SIM |
