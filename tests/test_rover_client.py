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


def test_stop_wins():
    hw = HW()
    r = sc.Rover(hw, lambda s: None)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 1})
    r.on_command({"type": "stop"})
    assert r.state == "stopped" and hw.cmds[-1] == "stop"
