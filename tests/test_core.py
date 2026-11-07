import pytest

from osprey.clock import FakeClock, OffsetEstimator, ScenarioClock
from osprey.geo import LatLon, ShipPose, horizontal_distance_m
from osprey.store import EventStore


def test_store_idempotent_and_ordered():
    s = EventStore()
    assert s.append({"event_id": "b", "type": "x", "capture_ts": 2.0})
    assert s.append({"event_id": "a", "type": "x", "capture_ts": 1.0})
    assert not s.append({"event_id": "a", "type": "x", "capture_ts": 9.0})
    assert [e["event_id"] for e in s.history()] == ["a", "b"]
    assert s.count() == 2


def test_offset_estimator():
    e = OffsetEstimator()
    assert e.quality == "unknown"
    assert e.to_server(5.0, 100.0) == 100.0
    # sender clock is 1000 s behind the server; 40 ms RTT
    for i in range(4):
        e.add(10.0 + i, 1010.02 + i, 10.04 + i)
    assert e.quality == "synced"
    assert e.offset == pytest.approx(1000.0, abs=1e-6)
    assert e.to_server(20.0, 1020.5) == pytest.approx(1020.0)
    assert e.to_server(30.0, 1020.5) == 1020.5  # never in the future


def test_scenario_clock_multiplier_continuity():
    c = FakeClock()
    sc = ScenarioClock(c, 60)
    c.advance(10)
    assert sc.sim_elapsed() == pytest.approx(600)
    sc.set_multiplier(120)
    assert sc.sim_elapsed() == pytest.approx(600)
    c.advance(1)
    assert sc.sim_elapsed() == pytest.approx(720)


def test_ship_camera_point():
    pose = ShipPose(42.35, -70.80, heading_deg=0, cam_bearing_rel=90)
    p = pose.camera_point(0.0, 2.0)  # 2 m straight out to starboard = east
    assert p.lat == pytest.approx(42.35)
    assert p.lon > -70.80
    assert horizontal_distance_m(pose.origin, p) == pytest.approx(2.0, abs=1e-3)
