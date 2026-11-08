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


class PanHW(HW):
    has_pan = True

    def __init__(self):
        super().__init__()
        self.pans = []

    def set_pan(self, deg):
        self.pans.append(round(deg, 2))


def _pan_rover(monkeypatch, t):
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    hw = PanHW()
    r = sc.Rover(hw, lambda s: None)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 0.0})
    r.tick()
    r.tick()
    t[0] += drive_window(0.0) + 0.1
    r.tick()
    r.tick()
    assert r.state == "searching"
    return r, hw


def test_pan_search_sweeps_camera_before_spinning_body(monkeypatch):
    t = [1000.0]
    r, hw = _pan_rover(monkeypatch, t)
    seen = []
    for _ in range(60):  # 6 s of ticks
        t[0] += 0.1
        r.tick()
        seen.append((r.pan_deg, hw.cmds[-1]))
    pans = [p for p, _ in seen]
    step = sc.PAN_SWEEP_DEG_PER_S * 0.1
    assert max(pans) >= sc.PAN_SWEEP_DEG - 1e-6 and min(pans) <= -sc.PAN_SWEEP_DEG + step
    assert ("stop" in [c for _, c in seen])                      # body still while sweeping
    assert (0.0, sc.SEARCH_TURN) in [c for _, c in seen]        # then a body spin step


def test_approach_centres_camera_and_body_turns_by_full_bearing(monkeypatch):
    """One steerer at a time: approaching re-centres the pan and the body turns toward the
    bearing the pan was holding (pan + body together overshot on the venue rover)."""
    t = [1000.0]
    r, hw = _pan_rover(monkeypatch, t)
    r._set_pan(20.0)                         # search sweep found it with the camera 20 deg right
    r.on_local([box(0.5, 0.5, 0.1)])         # centred in the image -> bearing +20 deg
    r.tick()
    assert r.state == "approaching"
    r.tick()
    assert r.pan_deg == 0.0                  # camera back to straight ahead
    turn = hw.cmds[-1][1]
    assert sc.APPROACH_MIN_TURN <= turn <= sc.APPROACH_MAX_TURN   # body turns right, bounded


def test_no_turn_on_a_stale_sighting(monkeypatch):
    t = [1000.0]
    r, hw = _pan_rover(monkeypatch, t)
    r._set_pan(0.0)
    r.on_local([box(0.8, 0.5, 0.1)])
    r.tick()
    r.tick()
    assert hw.cmds[-1][1] > 0                # fresh: turns toward it
    t[0] += sc.TURN_FRESH_S + 0.05           # blurred frames: no new sighting
    r.tick()
    assert hw.cmds[-1][1] == 0.0             # holds the turn instead of turning blind


def test_pan_corrects_once_per_sighting(monkeypatch):
    t = [1000.0]
    r, hw = _pan_rover(monkeypatch, t)
    r._set_pan(0.0)
    r.on_local([box(0.7, 0.5, 0.1)])
    r.tick()
    p1 = r.pan_deg
    r.tick()  # no new frame: no second correction
    assert r.pan_deg == p1


def test_at_the_ball_camera_stays_centred_and_body_turns(monkeypatch):
    """One steerer at the ball too: pan + body together oscillated on the venue rover."""
    monkeypatch.setattr(sc, "ARRIVE_BOX_H", sc.ARRIVE_BY_TARGET["green"])
    t = [1000.0]
    r, hw = _pan_rover(monkeypatch, t)
    r._set_pan(0.0)
    r.on_local([box(0.5, 0.5, 0.5)])
    r.tick()
    r.tick()
    assert r.state == "arrived"
    t[0] += 0.1
    r.on_local([box(0.56, 0.5, 0.5)])        # small move right: inside the hold band
    r.tick()
    assert r.pan_deg == 0.0 and hw.cmds[-1] == "stop"
    t[0] += 0.1
    r.on_local([box(0.7, 0.5, 0.5)])         # well off-centre: the body turns, camera stays put
    r.tick()
    assert r.pan_deg == 0.0 and hw.cmds[-1][0] == 0.0 and hw.cmds[-1][1] > 0


def test_pulse_servo_mapping_and_limits():
    calls = []
    s = sc.PulseServo(lambda i, p, ms: calls.append((i, p, ms)), servo_id=2, center_us=1500,
                      us_per_deg=10.0, sign=-1.0, move_ms=50, limit_deg=80)
    s.set(0)
    s.set(30)
    s.set(200)
    assert calls == [(2, 1500, 50), (2, 1200, 50), (2, 700, 50)]


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


def test_selftest_skip_sends_no_wheel_command(monkeypatch):
    ch = FakeChassis()
    hw = sc.HiwonderHardware(chassis=ch)
    answers = iter(["s", "s", "s", "s"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    sc.selftest(hw)
    assert all(c == (0, 0, 0) for c in ch.calls)   # only stops, never a move


def test_pan_right_is_lower_pulse_on_the_venue_rover():
    """Verified on the TurboPi: pulse 1167 turned the camera right, so +30 deg (right) -> 1167."""
    calls = []
    s = sc.PulseServo(lambda i, p, ms: calls.append((i, p)), 1, sign=-1.0)
    s.set(30.0)
    s.set(-30.0)
    assert calls == [(1, 1167), (1, 1833)]


def test_lock_window_moves_with_the_pan(monkeypatch):
    """Panning right shifts the ball left in the image: the lock must not drop it for that."""
    t = [100.0]
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    r = sc.Rover(PanHW(), lambda s: None)
    r.on_local({"bbox": (0.6, 0.4, 0.8, 0.6), "confidence": 0.9})     # locked at x = 0.7
    r._set_pan(20.0)                                                     # camera turns right 20 deg
    assert abs(r.lock_centre[0] - (0.7 - 20.0 / sc.CAM_HFOV_DEG)) < 1e-9
    # the ball now appears where the pan put it, well over the old gate from 0.7: still our lock
    nx = 0.7 - 20.0 / sc.CAM_HFOV_DEG
    t[0] += 0.1
    r.on_local([{"bbox": (nx - 0.1, 0.4, nx + 0.1, 0.6), "confidence": 0.9}])
    assert r.local_ts == t[0]


class TiltHW(PanHW):
    tilt_base_us = 1000.0

    def __init__(self):
        super().__init__()
        self.tilts = []

    def set_tilt(self, us):
        self.tilts.append(us)


def _tilt_rover(monkeypatch, t):
    monkeypatch.setattr(sc.time, "time", lambda: t[0])
    hw = TiltHW()
    r = sc.Rover(hw, lambda s: None)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 0.0})
    r.on_local([box(0.5, 0.5, 0.1)])
    r.tick()
    r.tick()
    assert r.state == "approaching"
    return r, hw


def test_tilt_follows_a_low_ball_down_and_moves_the_lock(monkeypatch):
    t = [2000.0]
    r, hw = _tilt_rover(monkeypatch, t)
    t[0] += 0.1
    r.on_local([box(0.5, 0.8, 0.15)])        # ball low in the frame as the rover closes in
    r.tick()
    assert r.tilt_us == 1000.0 + sc.TILT_STEP_US and hw.tilts[-1] == r.tilt_us
    assert r.lock_centre[1] < 0.8            # window moved up with the tilt


def test_lost_out_the_bottom_looks_down_up_to_the_limit(monkeypatch):
    t = [2000.0]
    r, hw = _tilt_rover(monkeypatch, t)
    t[0] += 0.1
    r.on_local([box(0.5, 0.75, 0.2)])
    r.tick()
    for _ in range(18):                      # ball gone: keep looking down, never past the limit
        t[0] += 0.15                         # (2.7 s: before LOST_TO_SEARCH_S gives up)
        r.tick()
    assert r.state == "approaching" and r.tilt_us == sc.TILT_DOWN_LIMIT_US


def test_dispatch_resets_the_tilt(monkeypatch):
    t = [2000.0]
    r, hw = _tilt_rover(monkeypatch, t)
    r._set_tilt(1400.0)
    r.on_command({"type": "dispatch", "heading_deg": 0, "distance_m": 0.0})
    assert r.tilt_us == 1000.0


def test_search_restores_the_start_tilt(monkeypatch):
    t = [2000.0]
    r, hw = _tilt_rover(monkeypatch, t)
    t[0] += 0.1
    r.on_local([box(0.5, 0.75, 0.2)])
    r.tick()
    for _ in range(25):                      # lost out the bottom, then gives up
        t[0] += 0.2
        r.tick()
    assert r.state == "searching" and r.tilt_us == 1000.0
