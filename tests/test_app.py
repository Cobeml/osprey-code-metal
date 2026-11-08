"""End-to-end checks of the FastAPI app with sim nodes (no hardware)."""
import importlib
import io
import json
import struct
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture(scope="module")
def client(tmp_path_factory, monkeypatch_module):
    monkeypatch_module.setenv("OSPREY_RUNTIME_DIR", str(tmp_path_factory.mktemp("rt")))
    monkeypatch_module.setenv("OSPREY_DETECTOR", "none")
    import osprey.app as appmod
    appmod = importlib.reload(appmod)
    with TestClient(appmod.app) as c:
        c.ground = appmod.ground
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def cmd(client, c, **args):
    return client.post("/api/commands", json={"command_id": f"{c}-{time.time()}", "cmd": c, "args": args}).json()


def test_display_gets_state_then_frames_then_history(client):
    time.sleep(0.5)
    cmd(client, "manual_mob")
    with client.websocket_connect("/ws") as ws:
        first = ws.receive()
        assert first.get("text") and json.loads(first["text"])["type"] == "state"
        kinds = []
        hist_seen = False
        for _ in range(20):
            m = ws.receive()
            if m.get("bytes"):
                kinds.append("frame")
            else:
                t = json.loads(m["text"])["type"]
                kinds.append(t)
                if t == "history":
                    hist_seen = True
                    assert json.loads(m["text"])["history"] is True
                    break
        assert hist_seen
        assert kinds.index("history") > 0 and kinds[0] == "frame"  # current video before backlog
    cmd(client, "end_incident")


def test_command_ack_is_idempotent(client):
    cmd(client, "manual_mob")
    body = {"command_id": "end-x", "cmd": "end_incident"}
    a1 = client.post("/api/commands", json=body).json()
    a2 = client.post("/api/commands", json=body).json()
    assert a1["ok"] and a2["ok"] and a2["duplicate"]


def test_scout_ws_takes_over_node(client):
    img = Image.new("RGB", (64, 48), (0, 80, 120))
    b = io.BytesIO()
    img.save(b, "JPEG")
    with client.websocket_connect("/ws/scout?node=B") as ws:
        for seq in range(1, 6):
            h = json.dumps({"node_id": "B", "session_id": "t1", "seq": seq,
                            "capture_ts_ms": time.time() * 1000, "width": 64, "height": 48}).encode()
            ws.send_bytes(struct.pack("<I", len(h)) + h + b.getvalue())
            time.sleep(0.05)
        ws.send_text(json.dumps({"ping": time.time() * 1000}))
        for _ in range(5):
            m = json.loads(ws.receive_text())
            if "pong" in m:
                break
        assert "pong" in m
        time.sleep(0.3)
        st = client.get("/api/state").json()
        assert st["nodes"]["B"]["source"] == "ws"
        assert st["nodes"]["B"]["session_id"] == "t1"
    cmd(client, "demo_source", node="B", source="sim")


def test_tunnel_only_exposes_scout(client):
    h = {"host": "abc-def.trycloudflare.com"}
    assert client.get("/scout", headers=h).status_code == 200
    assert client.get("/", headers=h).status_code == 403
    assert client.get("/api/state", headers=h).status_code == 403
    assert client.post("/api/commands", json={"cmd": "manual_mob"}, headers=h).status_code == 403
    assert client.get("/static/app.js", headers=h).status_code == 403
    assert client.get("/", headers={"host": "169.254.50.2:8000"}).status_code == 200


def test_rover_launches_on_mob_and_gets_fix_on_confirm(client):
    cmd(client, "end_incident")
    g = client.ground
    plan = g.dispatch_plan()
    assert plan["basis"].startswith("default")
    g.ship_ball = {"x_m": 1.0, "z_m": 2.0, "ts": time.time(), "source": "aurora"}
    plan = g.dispatch_plan()
    assert plan["basis"].startswith("deck-camera")
    assert plan["heading_deg"] == pytest.approx(26.6, abs=0.1)
    assert plan["distance_m"] == pytest.approx(2.236 - 0.4, abs=0.01)
    g.ship_ball = None
    assert cmd(client, "manual_mob")["ok"]
    ds = g.dispatch_state
    assert ds and ds["status"] == "dispatched" and ds["handoff"] is None
    assert not cmd(client, "dispatch")["ok"]  # no manual dispatch any more
    # confirm a drone sighting -> its fix is handed to the rover
    from osprey.incident import Sighting
    la = g.ship.camera_point(0.0, 30.0)
    from osprey.contracts import Location
    s = Sighting("t:1", "A", "sA", 1, time.time(), 1, (0.4, 0.4, 0.5, 0.5), 0.9,
                 Location(lat=la.lat, lon=la.lon, provenance="simulated", quality="good"), None)
    g.engine.last_accepted = s
    g.handoff_to_rover()
    h = g.dispatch_state["handoff"]
    assert h["from_node"] == "A" and h["range_m"] == pytest.approx(30.0, abs=0.5)
    cmd(client, "end_incident")
    assert g.dispatch_state is None


def test_real_ship_trigger_off_until_calibrated(client):
    g = client.ground
    cmd(client, "end_incident")
    g.trigger_enabled = False
    g.trigger.reset()
    t0 = time.time()
    for i, z in enumerate([1.0, 1.2, 1.8, 1.8, 1.8, 1.8]):
        g.ingest_frame("ship", b"\xff\xd8\xff\xd9", "aur-1", 1000 + i, t0 + i * 0.07, t0 + i * 0.07,
                       "synced", [{"track_id": 1, "bbox": (0.4, 0.2, 0.6, 0.9), "confidence": 0.9,
                                   "cls": "person", "z_m": z, "x_m": 0.0}], source="aurora")
    assert g.engine.phase() != "OVERBOARD" or g.engine.incident.source != "shipcam"
    g.last_ship_dets = [{"track_id": 1, "bbox": (0.4, 0.2, 0.6, 0.9), "confidence": 0.9,
                         "cls": "person", "z_m": 1.63}]
    a = cmd(client, "set_rail", from_person=True)
    assert a["ok"] and "1.63" in a["message"] and g.trigger_enabled


def test_deck_cam_green_ball_becomes_fix_beside_ship(client):
    g = client.ground
    cmd(client, "end_incident")
    m = cmd(client, "manual_mob")
    assert m["ok"], m
    n = g.engine.nodes["ship"]          # ride on the ship camera's current session
    t0 = max(time.time(), (n.last_capture_ts or 0) + 0.01)   # earlier tests feed future-dated frames
    g.ingest_frame("ship", b"\xff\xd8\xff\xd9", n.session_id, n.last_seq + 10_000, t0, t0, "synced",
                   [{"track_id": 7, "bbox": (0.4, 0.4, 0.5, 0.5), "confidence": 0.9,
                     "cls": "green", "z_m": 1.6, "x_m": 0.0}], source="aurora")
    st = client.get("/api/state").json()
    fix = st["nodes"]["ship"]["last_accepted"]
    assert st["nodes"]["ship"]["pill"] == "TRACKING" and st["phase"] == "TRACKING"
    assert fix["location"]["provenance"] == "real_relative"
    from osprey.geo import LatLon, latlon_to_enu
    e, n = latlon_to_enu(LatLon(st["ship"]["lat"], st["ship"]["lon"]),
                         LatLon(fix["location"]["lat"], fix["location"]["lon"]))
    assert abs((e * e + n * n) ** 0.5 - 1.6) < 0.05      # 1.6 m from the ship, as measured


def test_deck_cam_red_ball_is_not_a_fix(client):
    g = client.ground
    cmd(client, "end_incident")
    cmd(client, "manual_mob")
    t0 = time.time()
    g.ingest_frame("ship", b"\xff\xd8\xff\xd9", "aur-3", 1, t0, t0, "synced",
                   [{"track_id": 8, "bbox": (0.4, 0.4, 0.5, 0.5), "confidence": 0.9,
                     "cls": "red", "z_m": 1.6, "x_m": 0.0}], source="aurora")
    assert not client.get("/api/state").json()["nodes"]["ship"]["has_target"]


def test_drawer_sim_ship_ball_rides_on_ship_frames(client):
    cmd(client, "end_incident")
    cmd(client, "manual_mob")
    a = cmd(client, "demo_ship_ball", z_m=1.6, seconds=3)
    assert a["ok"], (a, client.get("/api/state").json()["phase"])
    g = client.ground
    n = g.engine.nodes["ship"]           # the ship camera's next frame (no ball seen) carries it
    t0 = max(time.time(), (n.last_capture_ts or 0) + 0.01)
    g.ingest_frame("ship", b"\xff\xd8\xff\xd9", n.session_id, n.last_seq + 1, t0, t0, "synced", [],
                   source="aurora")
    st = client.get("/api/state").json()
    assert st["nodes"]["ship"]["has_target"]
    assert st["nodes"]["ship"]["last_accepted"]["location"]["provenance"] == "simulated"


def test_rover_report_with_uwb_range_reaches_the_display_state(client):
    client.ground.rover_report("idle", {"locked": False, "uwb_m": 1.37, "uwb_status": "ranging"})
    ro = client.get("/api/state").json()["rover_onboard"]
    assert ro["uwb_m"] == 1.37 and ro["state"] == "idle" and ro["ts"] > 0
