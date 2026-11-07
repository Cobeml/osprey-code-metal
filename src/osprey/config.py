"""Settings: defaults here, overridden by config.yaml (repo root or $OSPREY_CONFIG) and env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    # ship pose (simulated position, Massachusetts Bay)
    ship_lat: float = 42.35
    ship_lon: float = -70.80
    ship_heading_deg: float = 45.0
    cam_bearing_rel: float = 90.0  # deck camera looks out to starboard
    # node sources: ship: sim|aurora ; A/B: sim|ws
    source_ship: str = "sim"
    source_A: str = "sim"
    source_B: str = "sim"
    # ship-cam rail trigger
    rail_m: float = 1.5
    rail_hysteresis_m: float = 0.15
    rail_frames: int = 3
    cam_height_m: float = 1.1
    aurora_mode: int = 2
    aurora_flip: bool = False
    rail_row_frac: float = 0.0  # where to draw the rail on the real ship-cam video (0 = off)
    cam_fx: float = 424.0
    cam_fy: float = 425.0
    cam_cx: float = 320.0
    cam_cy: float = 198.0
    # scenario / drift
    scenario_multiplier: float = 60.0
    drift_particles: int = 1500
    env_fixture: str = ""  # path; empty = newest fixtures/env/massbay-*.json
    # scouts
    sim_fps: float = 10.0
    detector: str = "hailo"  # hailo|none
    hef_path: str = "/usr/share/hailo-models/yolov8s_h8.hef"
    # storage
    runtime_dir: str = str(ROOT / "runtime")
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        path = Path(os.environ.get("OSPREY_CONFIG", ROOT / "config.yaml"))
        data = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        names = {f.name: f for f in fields(cls)}
        for k, v in data.items():
            if k in names:
                setattr(s, k, v)
            else:
                s.extra[k] = v
        for name, f in names.items():
            env = os.environ.get(f"OSPREY_{name.upper()}")
            if env is not None and name != "extra":
                typ = type(getattr(s, name))
                setattr(s, name, typ(env) if typ is not bool else env.lower() in ("1", "true", "yes"))
        return s
