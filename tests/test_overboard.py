"""Ball lost from the deck camera + water sensor wet -> man overboard."""
import time

from osprey.nodes.water import parse_line
from osprey.overboard import BallWaterTrigger


def test_parse_line_reads_the_configured_pin():
    dry = "A 281 283 285 271 D 1 1 1 1 1 1 1"
    wet = "A 281 283 285 271 D 1 1 1 0 1 1 1"
    assert parse_line(dry, 5) is False
    assert parse_line(wet, 5) is True
    assert parse_line(wet, 4) is False
    assert parse_line("# water_probe ready", 5) is None
    assert parse_line("A 1 2 D 1", 5) is None


def test_needs_both_ball_lost_and_water():
    t = BallWaterTrigger(lost_after_s=0.5)
    assert t.update(0.0, wet=True) is None          # never saw the ball: not armed
    t.ball_seen(1.0, 0.1, 1.2)
    assert t.armed
    assert t.update(1.2, wet=True) is None          # ball still in view
    assert t.update(2.0, wet=False) is None         # ball lost but dry
    trig = t.update(2.1, wet=True)                  # lost + wet
    assert trig and trig["z_m"] == 1.2 and trig["x_m"] == 0.1
    assert t.update(2.2, wet=True) is None          # once per arming
    t.reset()
    assert not t.armed


def test_water_first_then_ball_lost():
    t = BallWaterTrigger(lost_after_s=0.5)
    t.ball_seen(0.0)
    assert t.update(0.2, wet=True) is None
    assert t.update(0.6, wet=True) is not None


class FakeWater:
    def __init__(self):
        self.wet, self.online, self.status, self.pin = False, True, "ok", 5

    def start(self):
        pass

    def stop(self):
        pass


def test_ground_opens_mob_and_rearms(tmp_path, monkeypatch):
    monkeypatch.setenv("OSPREY_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("OSPREY_DETECTOR", "none")
    monkeypatch.setenv("OSPREY_SOURCE_SHIP", "sim")
    from osprey.app import Ground
    from osprey.config import Settings
    g = Ground(Settings.load())
    g.water = FakeWater()
    now = g.clock.now()
    g.ball_trigger.ball_seen(now - 2.0, 0.0, 1.5)
    g.check_overboard()
    assert not g.engine.active                      # dry
    st = g.state()["overboard"]
    assert st["armed"] and not st["ball_in_view"] and st["water"] == "dry"
    g.water.wet = True
    g.check_overboard()
    assert g.engine.active
    inc = g.engine.incident
    assert inc.source == "shipcam" and inc.detail["trigger"] == "ball_water"
    g.command(__import__("osprey.contracts", fromlist=["Command"]).Command(
        command_id=f"end-{time.time()}", type="end_incident", args={}))
    assert not g.engine.active and not g.ball_trigger.armed
    g.check_overboard()                             # needs the ball on deck again first
    assert not g.engine.active
