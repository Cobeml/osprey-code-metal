import pytest

from osprey.clock import FakeClock
from osprey.contracts import Command, Detection, FrameReport, Location
from osprey.geo import LatLon, enu_to_latlon, horizontal_distance_m
from osprey.incident import FRESH_S, IncidentEngine, is_fresh

O = LatLon(42.35, -70.80)


def loc(x=0.0, y=0.0, quality="good", provenance="simulated"):
    p = enu_to_latlon(O, x, y)
    return Location(lat=p.lat, lon=p.lon, quality=quality, provenance=provenance)


class Rig:
    def __init__(self):
        self.clock = FakeClock()
        n = iter(range(1, 100))
        self.eng = IncidentEngine(self.clock, id_factory=lambda ts: f"INC{next(n)}")
        self.seq = {}
        self.cmd = 0

    def mob(self, x=0.0, eid="mob1"):
        return self.eng.open_mob(eid, self.clock.now(), loc(x), "ship.jpg", "shipcam")

    def frame(self, node, dets=(), session="s1", seq=None, ts=None):
        k = (node, session)
        if seq is None:
            seq = self.seq.get(k, 0) + 1
        self.seq[k] = max(self.seq.get(k, 0), seq)
        r = FrameReport(node_id=node, session_id=session, seq=seq,
                        capture_ts=self.clock.now() if ts is None else ts,
                        received_ts=self.clock.now(), detections=list(dets))
        return self.eng.ingest(r)

    def run(self, type_, cid=None, **args):
        self.cmd += 1
        return self.eng.command(Command(command_id=cid or f"c{self.cmd}", type=type_, args=args))

    def candidates(self, node):
        return list(self.eng.nodes[node].candidates)


def det(track=1, conf=0.9, location=None):
    return Detection(track_id=track, bbox=(0.4, 0.3, 0.6, 0.9), confidence=conf, location=location)


def confirm_first(rig, node="A", x=0.0):
    rig.frame(node, [det(1, location=loc(x))])
    (cid,) = rig.candidates(node)
    ack, _ = rig.run("confirm", candidate_id=cid)
    assert ack.ok
    return cid


# ---------------------------------------------------------------- freshness
def test_freshness_boundary():
    assert is_fresh(100.0, 100.0 + 6.0)
    assert not is_fresh(100.0, 100.0 + 6.001)


def test_phase_freshness_exact_boundary():
    r = Rig()
    r.mob()
    confirm_first(r)
    r.clock.advance(FRESH_S)
    assert r.eng.phase() == "TRACKING"
    r.clock.advance(0.001)
    assert r.eng.phase() == "CONTACT_LOST"


def test_heartbeat_and_duplicates_do_not_refresh():
    r = Rig()
    r.mob()
    r.frame("A", [det(1, location=loc())], seq=1)
    ack, _ = r.run("confirm", candidate_id=r.candidates("A")[0])
    t0 = r.clock.now()
    r.clock.advance(5.0)
    # duplicate delivery of the same frame does nothing
    r.eng.ingest(FrameReport(node_id="A", session_id="s1", seq=1, capture_ts=t0,
                             received_ts=r.clock.now(), detections=[det(1, location=loc())]))
    # late delivery of an older frame does nothing to state
    r.eng.ingest(FrameReport(node_id="A", session_id="s1", seq=0, capture_ts=t0 - 1,
                             received_ts=r.clock.now(), detections=[det(1, location=loc())]))
    r.clock.advance(1.5)
    assert r.eng.nodes["A"].last_accepted.capture_ts == t0
    assert r.eng.phase() == "CONTACT_LOST"


# ---------------------------------------------------------------- phases
def test_story_phases():
    r = Rig()
    assert r.eng.phase() == "STANDBY"
    r.mob()
    assert r.eng.phase() == "OVERBOARD"
    r.frame("A", [det(1, location=loc(10))])
    assert r.eng.phase() == "CANDIDATE"
    r.run("confirm", candidate_id=r.candidates("A")[0])
    assert r.eng.phase() == "TRACKING"
    assert r.eng.following("A")
    r.clock.advance(7)
    r.eng.tick()
    assert r.eng.phase() == "CONTACT_LOST"
    assert r.eng.nodes["A"].lost
    seed = r.eng.drift_seed()
    assert seed["kind"] == "sighting"
    r.frame("A", [det(5, location=loc(30))])  # 20 m from last -> auto resume
    assert r.eng.phase() == "TRACKING"
    ack, ev = r.run("end_incident")
    assert ack.ok and r.eng.phase() == "ENDED"


def test_contact_drops_at_visual_loss_before_fix_goes_stale():
    """The search area starts expanding at visual loss (1.5 s), before the 6 s phase rule."""
    r = Rig()
    r.mob()
    r.frame("A", [det(1, location=loc(10))])
    r.run("confirm", candidate_id=r.candidates("A")[0])
    assert r.eng.any_contact()
    r.clock.advance(2)
    r.eng.tick()
    assert r.eng.nodes["A"].lost and not r.eng.any_contact()
    assert r.eng.phase() == "TRACKING"           # last fix still fresh (< 6 s)
    assert r.eng.drift_seed()["kind"] == "sighting"
    r.frame("A", [det(1, location=loc(12))])     # seen again -> contact, area suspended
    assert r.eng.any_contact()


def test_drift_seed_from_overboard_before_contact():
    r = Rig()
    r.mob(x=2.0)
    s = r.eng.drift_seed()
    assert s["kind"] == "overboard"


def test_one_incident_per_arming():
    r = Rig()
    assert r.mob(eid="m1")[0]["type"] == "mob"
    ev = r.mob(eid="m2")
    assert ev[0]["type"] == "mob_ignored"
    assert r.eng.incident.incident_id == "INC1"
    r.run("end_incident")
    assert r.mob(eid="m3")[0]["type"] == "mob"
    assert r.eng.incident.incident_id == "INC2"
    assert r.mob(eid="m3") == []  # duplicate MOB event


# ---------------------------------------------------------------- association
@pytest.mark.parametrize("dist,auto", [(49.9, True), (50.0, True), (50.1, False)])
def test_second_node_first_association(dist, auto):
    r = Rig()
    r.mob()
    confirm_first(r, "A", x=0.0)
    r.frame("B", [det(7, location=loc(dist))])
    assert r.eng.nodes["B"].has_target is auto
    assert (len(r.candidates("B")) == 0) is auto


@pytest.mark.parametrize("dist,auto", [(49.9, True), (50.0, True), (50.1, False)])
def test_reacquisition_uses_this_nodes_last_location(dist, auto):
    r = Rig()
    r.mob()
    confirm_first(r, "A", x=0.0)
    # B associates near A, then B moves its last sighting to x=100 via track continuity
    r.frame("B", [det(2, location=loc(10))])
    assert r.eng.nodes["B"].has_target
    r.frame("B", [det(2, location=loc(100))])
    r.clock.advance(2.0)
    r.frame("A", [])
    r.frame("B", [])
    assert r.eng.nodes["B"].lost
    # A's latest location is x=0; B's last before loss is x=100. Reference must be B's own.
    r.frame("B", [det(9, location=loc(100 + dist))])
    assert r.eng.nodes["B"].has_target and (not r.eng.nodes["B"].lost) is auto
    assert (len(r.candidates("B")) == 0) is auto


def test_reacquisition_beyond_50_keeps_prior_sighting_and_confirms():
    r = Rig()
    r.mob()
    confirm_first(r, "A", x=0.0)
    prior = r.eng.nodes["A"].last_accepted
    r.clock.advance(3)
    r.eng.tick()
    r.frame("A", [det(4, location=loc(80))])
    assert r.eng.nodes["A"].last_accepted is prior
    assert r.eng.phase() == "CANDIDATE"
    ack, _ = r.run("confirm", candidate_id=r.candidates("A")[0])
    assert ack.ok and r.eng.phase() == "TRACKING"


@pytest.mark.parametrize("bad", [None, "unreliable", "none"])
def test_missing_or_unreliable_location_requires_confirm(bad):
    r = Rig()
    r.mob()
    confirm_first(r, "A")
    if bad is None:
        l = None
    elif bad == "none":
        l = loc(1, provenance="none")
    else:
        l = loc(1, quality=bad)
    r.frame("B", [det(3, location=l)])
    assert not r.eng.nodes["B"].has_target
    assert len(r.candidates("B")) == 1


def test_first_candidate_always_needs_confirm():
    r = Rig()
    r.mob()
    r.frame("A", [det(1, location=loc(0))])
    assert not r.eng.nodes["A"].has_target
    assert r.eng.phase() == "CANDIDATE"


def test_multiple_candidates_highest_confidence_feasible_associates():
    r = Rig()
    r.mob()
    confirm_first(r, "A", x=0)
    r.frame("B", [det(1, 0.5, loc(10)), det(2, 0.8, loc(20)), det(3, 0.95, loc(200))])
    b = r.eng.nodes["B"]
    assert b.has_target and b.target_track == 2
    assert sorted(r.candidates("B")) == ["B:s1:1", "B:s1:3"]


# ---------------------------------------------------------------- ordering / sessions
def test_reordered_frames_cannot_rewind():
    r = Rig()
    r.mob()
    confirm_first(r, "A", x=0)
    r.clock.advance(1)
    r.frame("A", [det(1, location=loc(5))], seq=10)
    t_new = r.eng.nodes["A"].last_accepted.capture_ts
    ev = r.frame("A", [det(1, location=loc(1))], seq=5, ts=r.clock.now() - 0.5)
    assert ev and ev[0]["type"] == "late"
    assert r.eng.nodes["A"].last_accepted.capture_ts == t_new


def test_restarted_session_accepted_old_session_ignored():
    r = Rig()
    r.mob()
    confirm_first(r, "A", x=0)
    r.clock.advance(0.5)
    ev = r.frame("A", [det(1, location=loc(3))], session="s2", seq=1)
    assert any(e["type"] == "session_restart" for e in ev)
    # track ids restart with the session; the new sighting is within 50 m -> auto resume
    assert r.eng.nodes["A"].has_target and not r.eng.nodes["A"].lost
    before = r.eng.nodes["A"].last_accepted
    r.clock.advance(0.5)
    ev = r.frame("A", [det(1, location=loc(400))], session="s1", seq=99)
    assert ev[0]["type"] == "late"
    assert r.eng.nodes["A"].last_accepted is before
    assert r.eng.nodes["A"].session_id == "s2"


def test_restarted_session_never_reopens_closed_incident():
    r = Rig()
    r.mob()
    confirm_first(r)
    r.run("end_incident")
    r.frame("A", [det(1, location=loc(0))], session="s9", seq=1)
    assert r.eng.phase() == "ENDED"
    assert r.eng.incident.incident_id == "INC1"


# ---------------------------------------------------------------- end / commands
def test_end_is_final_and_idempotent():
    r = Rig()
    r.mob()
    confirm_first(r)
    a1, ev1 = r.run("end_incident", cid="end-1")
    a2, ev2 = r.run("end_incident", cid="end-1")
    a3, ev3 = r.run("end_incident", cid="end-2")
    assert a1.ok and ev1 and ev1[0]["type"] == "end"
    assert a2.duplicate and ev2 == []
    assert a3.ok and a3.message == "already ended" and ev3 == []
    ev = r.frame("A", [det(1, location=loc(0))])
    assert ev[0]["type"] == "late" and ev[0]["reason"] == "after end"
    assert r.eng.phase() == "ENDED"
    assert not r.eng.following("A")


def test_confirm_idempotent_by_command_id():
    r = Rig()
    r.mob()
    r.frame("A", [det(1, location=loc(0))])
    cid = r.candidates("A")[0]
    a1, ev1 = r.run("confirm", cid="x", candidate_id=cid)
    a2, ev2 = r.run("confirm", cid="x", candidate_id=cid)
    assert a1.ok and a2.ok and a2.duplicate
    assert ev2 == []
    assert sum(1 for e in ev1 if e["type"] == "confirm") == 1


def test_stop_follow_override():
    r = Rig()
    r.mob()
    confirm_first(r)
    assert r.eng.following("A")
    r.run("stop_follow")
    assert not r.eng.following("A")
    assert r.eng.phase() == "TRACKING"  # tracking continues, only following stops
    r.run("resume_follow")
    assert r.eng.following("A")


def test_visual_loss_vs_input_loss():
    r = Rig()
    r.mob()
    confirm_first(r, "A")
    r.clock.advance(1.0)
    r.frame("B", [])
    r.clock.advance(1.0)
    r.frame("B", [])
    r.frame("A", [])  # frames keep coming but no person -> visual loss
    snap = r.eng.snapshot()
    assert snap["nodes"]["A"]["pill"] == "CONTACT LOST"
    r.clock.advance(2.5)
    r.frame("A", [])
    r.eng.tick()
    snap = r.eng.snapshot()
    assert snap["nodes"]["B"]["pill"] == "NO VIDEO"
    assert snap["nodes"]["A"]["pill"] == "CONTACT LOST"


def test_geo_distance_sanity():
    a = loc(0)
    b = loc(50.0)
    assert horizontal_distance_m(LatLon(a.lat, a.lon), LatLon(b.lat, b.lon)) == pytest.approx(50.0, abs=0.01)


def test_deck_camera_ball_fix_pins_position_without_confirm():
    """A colour-classified ball with measured depth on the deck cam is a real fix beside the ship."""
    r = Rig()
    r.mob()
    r.frame("ship", [det(1, location=loc(1.5))])
    ship = r.eng.nodes["ship"]
    assert ship.has_target and r.eng.any_contact()
    assert r.eng.phase() == "TRACKING" and r.eng.node_pill(ship, r.clock.now()) == "TRACKING"
    seed = r.eng.drift_seed()
    assert seed["kind"] == "sighting" and seed["node_id"] == "ship"
    r.frame("ship", [])                       # ball out of view
    r.clock.advance(2)
    r.eng.tick()
    assert ship.lost and not r.eng.any_contact()   # area now expands from the deck-cam fix
    assert r.eng.drift_seed()["node_id"] == "ship"


def test_deck_camera_without_location_is_ignored():
    r = Rig()
    r.mob()
    r.frame("ship", [det(1)])
    assert not r.eng.nodes["ship"].has_target and r.eng.phase() == "OVERBOARD"
