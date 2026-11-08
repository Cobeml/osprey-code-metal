import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("scout_client", Path(__file__).parents[1] / "turbopi/scout_client.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


class HW(sc.NoHardware):
    def __init__(self):
        super().__init__()
        self.cmds = []

    def drive(self, f, t):
        self.cmds.append((round(f, 2), round(t, 2)))

    def stop(self):
        self.cmds.append("stop")


def test_dispatch_search_approach_arrive(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    hw, states = HW(), []
    r = sc.Rover(hw, states.append)
    r.on_command({"type": "dispatch", "heading_deg": 45, "distance_m": 0.5})
    r.tick()
    assert r.state == "turning" and hw.cmds[-1] == (0.0, 0.5)
    t[0] += 0.6
    r.tick()
    assert r.state == "driving"
    t[0] += 2.1
    r.tick()
    assert r.state == "searching"
    r.on_command({"type": "follow", "err": [0.1, 0.0], "size": 0.2})
    r.tick()
    assert r.state == "approaching"
    r.tick()
    assert hw.cmds[-1][0] > 0  # creeping forward while roughly centred
    t[0] += 1.5
    r.tick()
    assert hw.cmds[-1] == "stop"  # stale follow -> hold
    r.on_command({"type": "follow", "err": [0.0, 0.0], "size": 0.5})
    r.tick()
    assert r.state == "arrived"
    assert states == ["turning", "driving", "searching", "approaching", "arrived"]


def _searching_rover(monkeypatch, t):
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    hw, states = HW(), []
    r = sc.Rover(hw, states.append)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 0.0})
    r.tick()
    r.tick()
    r.tick()
    assert r.state == "searching"
    return r, hw


def test_onboard_green_steers_when_ground_has_no_box(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local({"bbox": (0.45, 0.4, 0.55, 0.6), "confidence": 0.8}, decoys=1)
    r.tick()
    assert r.state == "approaching" and r.guide_src == "onboard"
    r.on_local({"bbox": (0.3, 0.2, 0.7, 0.7), "confidence": 0.9})
    r.tick()
    assert r.state == "arrived"
    ob = r.onboard()
    assert ob["color"] == "green" and ob["decoys"] == 0 and ob["guide"] == "onboard"


def test_ground_follow_outranks_onboard(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local({"bbox": (0.0, 0.4, 0.1, 0.5), "confidence": 0.8})   # far left onboard
    r.on_command({"type": "follow", "err": [0.3, 0.0], "size": 0.1})  # ground says right
    r.tick()
    r.tick()
    assert r.guide_src == "ground" and hw.cmds[-1][1] > 0


def test_no_green_means_keep_searching(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local(None, decoys=2)  # only red decoys in view
    r.tick()
    assert r.state == "searching" and r.onboard()["color"] is None


def test_stop_wins():
    hw = HW()
    r = sc.Rover(hw, lambda s: None)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 1})
    r.on_command({"type": "stop"})
    assert r.state == "stopped" and hw.cmds[-1] == "stop"
