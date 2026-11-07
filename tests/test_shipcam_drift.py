import numpy as np
import pytest

from osprey.clock import FakeClock, ScenarioClock
from osprey.contracts import Location
from osprey.drift import DriftEstimator, Forcing, LeewayEnsemble, polygon_area
from osprey.geo import LatLon
from osprey.shipcam import RailTrigger, box_depth_m


def walk(trig, zs, t0=0.0, dt=0.07, tid=1):
    out = []
    for i, z in enumerate(zs):
        r = trig.update(t0 + i * dt, [(tid, z, 0.0)] if z is not None else [])
        if r:
            out.append(r)
    return out


def test_trigger_needs_arming_and_consecutive_frames():
    t = RailTrigger(rail_m=1.5)
    # a person appearing beyond the rail without first being on deck never triggers
    assert walk(t, [2.0] * 10) == []
    t.reset()
    fired = walk(t, [1.0, 1.2, 1.4, 1.6, 1.7, 1.7, 1.66])
    assert len(fired) == 1 and fired[0]["reason"] == "crossed rail"


def test_trigger_hysteresis_and_once_per_arming():
    t = RailTrigger(rail_m=1.5)
    # hovering just past the rail (inside hysteresis) does not fire
    assert walk(t, [1.2, 1.6, 1.6, 1.6, 1.6, 1.4]) == []
    fired = walk(t, [1.2, 1.8, 1.8, 1.8, 1.0, 1.8, 1.8, 1.8], t0=1.0)
    assert len(fired) == 1
    t.reset()
    assert len(walk(t, [1.0, 1.8, 1.8, 1.8], t0=5.0)) == 1


def test_trigger_on_loss_near_rail():
    t = RailTrigger(rail_m=1.5)
    fired = walk(t, [1.0, 1.25, 1.3, None, None, None, None, None, None, None])
    assert len(fired) == 1 and "lost" in fired[0]["reason"]
    t2 = RailTrigger(rail_m=1.5)
    assert walk(t2, [1.0, 0.9, 0.8, None, None, None, None, None, None]) == []  # walked away


def test_box_depth_inner_median():
    d = np.zeros((400, 640), np.uint16)
    d[100:300, 200:300] = 1800
    d[100:120, 200:300] = 500  # edge clutter outside the inner 50%
    assert box_depth_m(d, (200, 100, 300, 300)) == pytest.approx(1.8)


def test_drift_area_grows_while_unseeded():
    ens = LeewayEnsemble(LatLon(42.35, -70.8), Forcing.default(), n=800,
                         rng=np.random.default_rng(1))
    areas = []
    for t in range(0, 3600 * 3, 900):
        ens.advance_to(t)
        areas.append(polygon_area(ens.hull(0.9)))
    assert all(b > a for a, b in zip(areas[1:], areas[2:]))


def test_drift_suspended_while_fresh_and_seeded_from_sighting():
    est = DriftEstimator(Forcing.default(), n=300)
    loc = Location(lat=42.35, lon=-70.8)
    seed = {"kind": "sighting", "ts": 100.0, "location": loc, "node_id": "A"}
    sim_at = lambda t: (t - 100.0) * 60.0  # noqa: E731
    assert est.update(seed, True, sim_at, 60, real_now=101) is None
    out = est.update(seed, False, sim_at, 60, real_now=107)
    assert out["seed_kind"] == "sighting"
    assert out["sim_elapsed_s"] == pytest.approx(420)  # 7 real s at 60x since the sighting


def test_multiplier_does_not_change_freshness():
    from osprey.incident import IncidentEngine
    c = FakeClock()
    sc = ScenarioClock(c, 60)
    eng = IncidentEngine(c)
    eng.open_mob("m", c.now(), Location(lat=42.35, lon=-70.8), None, "manual")
    sc.set_multiplier(600)
    c.advance(5.9)
    assert eng.phase() == "OVERBOARD"
    assert sc.sim_elapsed() == pytest.approx(5.9 * 600)


def test_scenario_clock_fast_only_when_unseen():
    c = FakeClock()
    sc = ScenarioClock(c, 60, fast=True)
    t0 = c.now()
    c.advance(10)
    sc.set_fast(False)
    c.advance(10)
    assert sc.sim_elapsed() == pytest.approx(610)
    assert sc.sim_at(t0 + 5) == pytest.approx(300)
    assert sc.sim_at(t0 + 15) == pytest.approx(605)
