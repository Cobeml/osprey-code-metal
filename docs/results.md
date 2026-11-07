# Results — measured evidence

Measured November 7, 2026 on the demo hardware unless marked. "Sim" means the Phase 2 simulated node stood in for that feed, and the UI labels it SIM.

## Setup

| Item | Version |
|---|---|
| Ground processor | Raspberry Pi 5 16 GB, Raspberry Pi OS (Debian 13 trixie), kernel 6.12.47, Python 3.13.5 |
| Accelerator | Hailo-8, firmware 4.23.0, HailoRT / `hailo_platform` 4.23.0, `yolov8s_h8.hef` (on-chip NMS) |
| Deck camera | Deptrum Aurora 930, SDK aurora900 v1.1.4, mode 2 (640×400 RGB + aligned depth) |
| Server | FastAPI + uvicorn (stock asyncio loop; see below), SQLite event log |
| Display | MacBook Air M1 browser over wired Ethernet (169.254.50.2) |

## Measurements

| Measure | Target | Result | How |
|---|---|---|---|
| Hailo person detector | — | 84 fps standalone (11–12 ms inference); 12–14 ms per frame in the server | `python -m osprey.perception.detector`, `/api/calibration` timing |
| Deck camera pipeline (bridge → JPEG → Hailo → depth) | ≥ 10 fps | 14.5 fps (camera limit ~14) | `/api/state` node fps with `source_ship=aurora` |
| Sim story end to end | completes | PASS on the Pi, every phase reached | `scripts/sim_story.py http://169.254.50.2:8000` |
| Auto MOB, **sim** deck cam | ≤ 2 s from rail crossing | 1.28–1.40 s from *walk start* (the crossing itself is ~0.8 s into the walk, so ≈ 0.5 s after crossing) | `scripts/sim_story.py` |
| Auto MOB, real Aurora | ≤ 2 s | *pending H1 calibration* | |
| Display LINK LOST detection | 1.5 s rule | 1.53 s after the last message | `scripts/measure_outage.py --inject 5` |
| Recovery after a 5 s **software** outage | ≤ 3 s | current state 0.06–0.07 s after the outage ended, history 5–9 ms later (19 events during tracking) | `scripts/measure_outage.py --inject 5` |
| Ground keeps tracking during outage | yes | phase TRACKING throughout, events archived and replayed | same, plus `/api/state` |
| Recovery after a real cable pull | ≤ 3 s | *pending (needs the user present)* | `scripts/measure_outage.py --watch 60` |
| Phone scout fps / latency through tunnel | ≥ 10 fps, ≤ 1 s | *pending (cloudflared + H2)* | |
| Drift forcing | real snapshot | Open-Meteo 2026-11-07 21:00 UTC, 42.35N 70.80W: wind 2.8 m/s from 327°, current 0.17 m/s toward 304° (`fixtures/env/massbay-20261107.json`) | `scripts/fetch_env.py` |
| Pi CPU, three sim feeds + UI | — | ~20% of one core (uvicorn) | `top` |

## Findings worth knowing

- **uvloop froze the server.** With uvicorn's default uvloop, starting the Aurora bridge subprocess while Hailo inference ran on a worker thread froze the event loop (stack dump: Hailo `infer()` and the main thread both stuck). With the stock asyncio loop (`--loop asyncio`) it runs cleanly; `scripts/run_pi.sh` pins it.
- **HailoRT calls stay on one thread.** The detector owns a single-thread executor that creates the vstreams and runs every inference.
- **`cv::imencode(".jpg")` segfaults next to the Deptrum SDK** (likely a libjpeg clash). The bridge outputs raw BGR and the Python side encodes JPEG in about 2 ms.
- **Drift and scenario clock.** The scenario clock runs at the multiplier (default 60×) only while no sighting is fresh, so the drift estimate (PIW-1) and the simulated person truth (PIW-2, separate noise) share one timeline. Freshness and link timing always use the real clock (unit-tested).
