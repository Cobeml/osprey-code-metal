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


def drive_window(distance_m):
    return (distance_m + sc.EXTRA_SEARCH_M) / sc.DRIVE_M_PER_S


def box(cx, cy, h, conf=0.8):
    return {"bbox": (cx - h / 2, cy - h / 2, cx + h / 2, cy + h / 2), "confidence": conf}


def test_dispatch_search_approach_arrive(monkeypatch):
    monkeypatch.setattr(sc, "ARRIVE_BOX_H", sc.ARRIVE_BY_TARGET["green"])
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
    t[0] += drive_window(0.5) + 0.1
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


def _driving_rover(monkeypatch, t, distance_m=0.0):
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    hw, states = HW(), []
    r = sc.Rover(hw, states.append)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": distance_m})
    r.tick()
    r.tick()
    assert r.state == "driving" and hw.cmds[-1] == (sc.DRIVE_SPEED, 0.0)
    return r, hw, states


def _searching_rover(monkeypatch, t):
    r, hw, _ = _driving_rover(monkeypatch, t)
    t[0] += drive_window(0.0) + 0.1
    r.tick()
    r.tick()
    assert r.state == "searching"
    return r, hw


def test_drives_until_green_is_recognised_then_locks_and_approaches(monkeypatch):
    monkeypatch.setattr(sc, "ARRIVE_BOX_H", sc.ARRIVE_BY_TARGET["green"])
    t = [1000.0]
    r, hw, states = _driving_rover(monkeypatch, t, distance_m=2.0)
    t[0] += 1.0
    r.tick()
    assert r.state == "driving"  # nothing seen yet: keep driving forward
    r.on_local([box(0.6, 0.5, 0.1)])
    r.tick()
    assert r.state == "approaching" and r.guide_src == "onboard" and r.locked()
    r.tick()
    assert hw.cmds[-1][0] > 0 and hw.cmds[-1][1] > 0  # forward and turning right toward it
    r.on_local([box(0.5, 0.5, 0.5)])
    r.tick()
    assert r.state == "arrived" and hw.cmds[-1] == "stop"
    assert "searching" not in states


def _arrived_rover(monkeypatch, t):
    monkeypatch.setattr(sc, "ARRIVE_BOX_H", sc.ARRIVE_BY_TARGET["green"])
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local([box(0.5, 0.5, 0.5)])
    r.tick()
    r.tick()
    assert r.state == "arrived"
    return r, hw


def test_arrived_turns_to_follow_a_sideways_ball(monkeypatch):
    t = [1000.0]
    r, hw = _arrived_rover(monkeypatch, t)
    r.on_local([box(0.62, 0.5, 0.5)])  # ball rolled right, still close
    r.tick()
    assert r.state == "arrived" and hw.cmds[-1][0] == 0.0 and hw.cmds[-1][1] > 0
    r.on_local([box(0.52, 0.5, 0.5)])  # re-centred
    r.tick()
    assert hw.cmds[-1] == "stop"


def test_arrived_drives_after_a_ball_moving_away(monkeypatch):
    t = [1000.0]
    r, hw = _arrived_rover(monkeypatch, t)
    r.on_local([box(0.55, 0.5, 0.2)])  # ball moved off: box shrank
    r.tick()
    assert r.state == "approaching"
    r.tick()
    assert hw.cmds[-1][0] > 0  # driving after it


def test_arrived_searches_when_ball_leaves_view(monkeypatch):
    t = [1000.0]
    r, hw = _arrived_rover(monkeypatch, t)
    t[0] += sc.STALE_S + 0.1
    r.tick()
    assert r.state == "arrived" and hw.cmds[-1] == "stop"
    t[0] += sc.LOST_TO_SEARCH_S
    r.tick()
    assert r.state == "searching"


def test_lock_ignores_a_second_green_blob(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local([box(0.3, 0.5, 0.1, conf=0.7)])
    r.tick()
    assert r.locked() and r.local["err"][0] < 0
    # a brighter green appears far right: the lock stays on the left one
    r.on_local([box(0.9, 0.5, 0.1, conf=0.95), box(0.32, 0.5, 0.11, conf=0.6)])
    assert r.local["err"][0] < 0 and abs(r.lock_centre[0] - 0.32) < 1e-9
    # only the far-away blob: not our target, lock is not moved
    r.on_local([box(0.9, 0.5, 0.1, conf=0.95)])
    assert abs(r.lock_centre[0] - 0.32) < 1e-9


def test_lost_lock_holds_then_searches_again(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local([box(0.5, 0.5, 0.1)])
    r.tick()
    assert r.state == "approaching"
    t[0] += sc.STALE_S + 0.1
    r.tick()
    assert r.state == "approaching" and hw.cmds[-1] == "stop"  # hold first
    t[0] += sc.LOST_TO_SEARCH_S
    r.tick()
    assert r.state == "searching" and r.lock_centre is None  # free to lock onto a new sighting


def test_onboard_lock_outranks_ground(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local([box(0.05, 0.45, 0.1)])                                 # rover sees it far left
    r.on_command({"type": "follow", "err": [0.3, 0.0], "size": 0.1})  # ground says right
    r.tick()
    r.tick()
    assert r.guide_src == "onboard" and hw.cmds[-1][1] < 0


def test_ground_steers_when_rover_sees_nothing(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_command({"type": "follow", "err": [0.3, 0.0], "size": 0.1})
    r.tick()
    r.tick()
    assert r.guide_src == "ground" and hw.cmds[-1][1] > 0


def test_no_green_means_keep_searching(monkeypatch):
    t = [1000.0]
    r, hw = _searching_rover(monkeypatch, t)
    r.on_local(None, decoys=2)  # only red decoys in view
    r.on_local([], decoys=2)
    r.tick()
    assert r.state == "searching" and r.onboard()["color"] is None
    assert hw.cmds[-1] == (0.0, sc.SEARCH_TURN)


def test_stop_wins():
    hw = HW()
    r = sc.Rover(hw, lambda s: None)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 1})
    r.on_command({"type": "stop"})
    assert r.state == "stopped" and hw.cmds[-1] == "stop"


def test_person_arrives_only_when_close(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    monkeypatch.setattr(sc, "ARRIVE_BOX_H", sc.ARRIVE_BY_TARGET["person"])
    hw = HW()
    r = sc.Rover(hw, lambda s: None)
    r.onboard_label = "person"
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 0.0})
    r.tick(); r.tick(); r.tick()
    r.on_command({"type": "follow", "err": [0.0, 0.0], "size": 0.6})  # person still a few m away
    r.tick()
    assert r.state == "approaching"
    r.on_local({"bbox": (0.3, 0.05, 0.7, 0.95), "confidence": 0.8})
    r.tick()
    assert r.state == "arrived"
    assert r.onboard()["label"] == "person"


class FakeChassis:
    def __init__(self):
        self.calls = []

    def set_velocity(self, speed, direction, yaw):
        self.calls.append((speed, direction, yaw))


def test_hiwonder_chassis_mapping():
    ch = FakeChassis()
    hw = sc.HiwonderHardware(chassis=ch)
    hw.drive(0.5, 0.0)
    assert ch.calls[-1] == (0.5 * sc.SDK_MAX_SPEED, sc.SDK_FORWARD_DEG, 0.0)
    hw.drive(-0.5, 0.0)
    assert ch.calls[-1][1] == sc.SDK_BACKWARD_DEG and ch.calls[-1][0] > 0
    hw.drive(0.0, 0.25)
    assert ch.calls[-1] == (0.0, sc.SDK_FORWARD_DEG, round(sc.SDK_YAW_SIGN * 0.25 * sc.SDK_MAX_YAW, 3))
    hw.drive(3.0, -3.0)  # out-of-range commands are clamped
    assert ch.calls[-1] == (sc.SDK_MAX_SPEED, sc.SDK_FORWARD_DEG, -sc.SDK_YAW_SIGN * sc.SDK_MAX_YAW)
    hw.stop()
    assert ch.calls[-1] == (0, 0, 0)


def test_selftest_always_ends_stopped(monkeypatch):
    ch = FakeChassis()
    hw = sc.HiwonderHardware(chassis=ch)
    answers = iter(["", "q"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    sc.selftest(hw)
    assert ch.calls[0][0] > 0 and ch.calls[-1] == (0, 0, 0)
