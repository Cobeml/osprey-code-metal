"""HiwonderSDK shim for the Pi 5 TurboPi image: wheel maths and servo call on a fake board."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "turbopi"))

from HiwonderSDK import _board, mecanum, Board  # noqa: E402


class FakeBoard:
    def __init__(self):
        self.calls = []

    def set_motor_duty(self, d):
        self.calls.append(("duty", d))

    def pwm_servo_set_position(self, t, p):
        self.calls.append(("pwm", t, p))


def fake(monkeypatch):
    b = FakeBoard()
    monkeypatch.setattr(_board, "_board", b)
    return b


def test_forward_drives_all_wheels_forward(monkeypatch):
    b = fake(monkeypatch)
    mecanum.MecanumChassis().set_velocity(50, 90, 0)
    assert b.calls[-1] == ("duty", [[1, -50], [2, 50], [3, -50], [4, 50]])  # left motors mirrored


def test_turn_in_place_and_stop_and_clamp(monkeypatch):
    b = fake(monkeypatch)
    c = mecanum.MecanumChassis()
    c.set_velocity(0, 90, 0.2)            # left wheels fwd, right back = clockwise (left motors mirrored)
    assert b.calls[-1] == ("duty", [[1, -25], [2, -25], [3, -25], [4, -25]])
    c.set_velocity(100, 90, 1.0)          # saturates instead of overflowing the board's range
    assert all(-100 <= v <= 100 for _, v in b.calls[-1][1])
    c.set_velocity(0, 0, 0)
    assert b.calls[-1] == ("duty", [[1, 0], [2, 0], [3, 0], [4, 0]])


def test_pan_servo_call(monkeypatch):
    b = fake(monkeypatch)
    Board.setPWMServoPulse(2, 1600, 60)
    Board.setPWMServoPulse(2, 9999, 0)
    assert b.calls == [("pwm", 0.06, [[2, 1600]]), ("pwm", 0.02, [[2, 2500]])]
