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
