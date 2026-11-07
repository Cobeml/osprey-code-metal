"""Osprey ground processor: FastAPI app, wiring, node loops."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .clock import Clock, ScenarioClock
from .config import ROOT, Settings
from .contracts import Command, Detection, FrameReport, Location
from .drift import DriftEstimator, Forcing
from .gateway import Gateway
from .follow import FollowController
from .geo import LatLon, ShipPose, latlon_to_enu
from .incident import IncidentEngine
from .nodes.aurora import AuroraNode
from .nodes.capture import CaptureNode, list_uvc
from .nodes.sim import SimScout, SimShipCam
from .nodes.ws_ingest import ScoutIngest
from .perception.detector import make_detector
from .perception.targets import detect_targets
from .scenario import Scenario
from .shipcam import RailTrigger
from .store import EventStore

log = logging.getLogger("osprey")
import faulthandler, signal, sys  # noqa: E401,E402
faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)

EVIDENCE_MIN_PERIOD_S = 0.5


class Ground:
    def __init__(self, settings: Settings, clock: Optional[Clock] = None):
        self.s = settings
        self.clock = clock or Clock()
        rt = Path(settings.runtime_dir)
        self.evidence_dir = rt / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.store = EventStore(str(rt / "osprey.sqlite"))
        self.engine = IncidentEngine(self.clock)
        self.ship = ShipPose(settings.ship_lat, settings.ship_lon, settings.ship_heading_deg,
                             settings.cam_bearing_rel)
        self.forcing = Forcing.load(settings.env_fixture)
        self.sclock = ScenarioClock(self.clock, settings.scenario_multiplier, fast=False)
        self.scenario = Scenario(self.ship, self.forcing, sim_at=self.sclock.sim_at)
        self.drift = DriftEstimator(self.forcing, settings.drift_particles)
        self.drift_view: Optional[dict] = None
        self.trigger = RailTrigger(settings.rail_m, settings.rail_hysteresis_m, settings.rail_frames)
        self.gateway = Gateway(self.clock)
        self.gateway.history_fn = self._history
        self.gateway.command_fn = self.handle_ws_command
        self.sources = {"ship": settings.source_ship, "A": settings.source_A, "B": settings.source_B}
        self.sim_ship = SimShipCam(settings.rail_m, settings.cam_height_m, settings.cam_fx,
                                   settings.cam_fy, settings.cam_cx, settings.cam_cy)
        self.labels = {"ship": settings.label_ship, "A": settings.label_A, "B": settings.label_B}
        self.targets = {"ship": settings.target_ship, "A": settings.target_A, "B": settings.target_B}
        self.drone, self.rover = settings.drone_node, settings.rover_node
        self.sim_scouts = {"A": SimScout("A", self.labels["A"].split("·")[-1].strip(), 1),
                           "B": SimScout("B", self.labels["B"].split("·")[-1].strip(), 2)}
        self.dispatch_state: Optional[dict] = None  # rover dispatch: {ts, status, plan}
        self.ship_ball: Optional[dict] = None       # ball fix on the deck camera (real relative)
        self.last_evidence: dict[str, float] = {}
        self.latest_jpeg: dict[str, bytes] = {}
        self.fps: dict[str, list[float]] = {}
        self.tasks: list[asyncio.Task] = []
        self.detector = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.aurora = AuroraNode(self, settings.aurora_mode, settings.aurora_flip)
        self.scouts = ScoutIngest(self)
        self.follow = FollowController()
        self.capture = CaptureNode(self, self.drone, settings.capture_device,
                                   settings.capture_file, settings.capture_fps)
        self.last_ship_dets: list[dict] = []
        self.calib_path = rt / "calibration.json"
        if self.calib_path.exists():
            c = json.loads(self.calib_path.read_text())
            self.trigger.rail_m = self.s.rail_m = float(c.get("rail_m", self.s.rail_m))
            self.s.rail_row_frac = float(c.get("rail_row_frac", self.s.rail_row_frac))

    # -------------------------------------------------------------- lifecycle
    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.detector = await asyncio.to_thread(make_detector, self.s.detector, self.s.hef_path)
        log.warning("detector: %s", type(self.detector).__name__ if self.detector else "none")
        self.tasks.append(asyncio.create_task(self.aurora.run()))
        self.tasks += self.scouts.start(("A", "B"))
        self.tasks.append(asyncio.create_task(self._state_loop()))
        self.tasks.append(asyncio.create_task(self._sim_loop()))

    async def stop(self) -> None:
        for t in self.tasks:
            t.cancel()

    # -------------------------------------------------------------- events
    def record(self, events: list[dict]) -> None:
        launch = handoff = False
        for e in events:
            if not self.store.append(e):
                continue
            t = e["type"]
            if t == "mob":
                loc = e.get("location")
                self.scenario.on_mob(Location(**loc) if loc else None, e["capture_ts"])
                self.drift.clear()
                launch = True
            elif t == "confirm":
                handoff = True
            elif t == "end":
                self.dispatch_state = None
                self.scenario.end()
                self.sim_ship.reset()
                self.trigger.reset()
                self.drift.clear()
            self.gateway.publish_event(e)
        # follow-ups go out after the events that caused them
        if launch:
            self.launch_rover()
        if handoff:
            self.handoff_to_rover()

    def _history(self) -> list[dict]:
        inc = self.engine.incident
        return self.store.history(inc.incident_id) if inc else []

    def save_evidence(self, node_id: str, name: str, jpeg: bytes) -> str:
        inc = self.engine.incident.incident_id if self.engine.incident else "standby"
        d = self.evidence_dir / inc
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(jpeg)
        return f"{inc}/{name}"

    # -------------------------------------------------------------- detection
    def detect(self, node_id: str, bgr) -> list[dict]:
        """Run this node's target detectors on a BGR frame (any thread)."""
        return detect_targets(self.targets.get(node_id, "person"), bgr, self.detector,
                              (self.s.green_hsv_lo, self.s.green_hsv_hi))

    # -------------------------------------------------------------- frames
    def ingest_frame(self, node_id: str, jpeg: bytes, session_id: str, seq: int,
                     capture_ts: float, received_ts: float, clock_quality: str,
                     dets: list[dict], width: int = 640, height: int = 400,
                     source: str = "sim") -> None:
        now = self.clock.now()
        self.latest_jpeg[node_id] = jpeg
        f = self.fps.setdefault(node_id, [])
        f.append(now)
        while f and now - f[0] > 2.0:
            f.pop(0)

        events: list[dict] = []
        image_ref = None
        if node_id == "ship":
            self.last_ship_dets = dets
            persons = [d for d in dets if d.get("cls", "person") == "person"]
            balls = [d for d in dets if d.get("cls") in ("ball", "green") and d.get("z_m")]
            if balls:
                b = max(balls, key=lambda d: d["confidence"])
                self.ship_ball = {"x_m": b.get("x_m", 0.0), "z_m": b["z_m"], "ts": capture_ts,
                                  "source": source}
            trig = self.trigger.update(capture_ts, [(d["track_id"], d.get("z_m"), d.get("x_m", 0.0))
                                                   for d in persons])
            if trig and self.engine.armed:
                p = self.ship.camera_point(trig["x_m"] or 0.0, trig["z_m"] or self.s.rail_m)
                prov = "real_relative" if source == "aurora" else "simulated"
                loc = Location(lat=p.lat, lon=p.lon, provenance=prov, quality="good",
                               accuracy_m=0.5 if prov == "real_relative" else None)
                eid = f"mob:{node_id}:{session_id}:{seq}"
                # open first so evidence lands in the new incident's folder
                events = self.engine.open_mob(eid, trig["ts"], loc, None, "shipcam",
                                              detail={**trig, "camera": source})
                if events and events[0]["type"] == "mob":
                    ref = self.save_evidence(node_id, f"mob-trigger-{seq}.jpg", jpeg)
                    self.engine.incident.mob_image_ref = ref
                    events[0]["image_ref"] = ref
            elif trig:
                self.trigger.fired = True
        else:
            if dets and self.engine.active and \
                    now - self.last_evidence.get(node_id, 0) >= EVIDENCE_MIN_PERIOD_S:
                image_ref = self.save_evidence(node_id, f"{node_id}-{session_id}-{seq}.jpg", jpeg)
                self.last_evidence[node_id] = now
            for d in dets:
                if d.get("location") is None:
                    loc = self.scenario.scout_location(node_id, capture_ts)
                    d["location"] = loc.model_dump() if loc else None

        report = FrameReport(
            node_id=node_id, session_id=session_id, seq=seq, capture_ts=capture_ts,
            received_ts=received_ts, clock_quality=clock_quality,
            detections=[Detection(track_id=d["track_id"], bbox=tuple(d["bbox"]),
                                  confidence=d["confidence"],
                                  location=Location(**d["location"]) if d.get("location") else None)
                        for d in dets],
            image_ref=image_ref,
        )
        events += self.engine.ingest(report)
        self.record(events)

        node = self.engine.nodes[node_id]
        boxes = []
        for d in dets:
            cid = f"{node_id}:{session_id}:{d['track_id']}"
            if node_id == "ship":
                st = "person" if d.get("cls", "person") == "person" else "ball"
            elif node.target_track == d["track_id"] and not node.lost and node.has_target:
                st = "tracking"
            elif cid in node.candidates:
                st = "candidate"
            else:
                st = "detection"
            boxes.append({"bbox": list(d["bbox"]), "track_id": d["track_id"], "state": st,
                          "candidate_id": cid if st == "candidate" else None,
                          "confidence": round(d["confidence"], 2),
                          "cls": d.get("cls"),
                          "z_m": round(d["z_m"], 2) if d.get("z_m") is not None else None})
        if node_id == self.rover and source == "ws":
            tb = next((b["bbox"] for b in boxes if b["state"] == "tracking"), None)
            msg = self.follow.on_frame(self.engine.following(self.rover), self.engine.follow_enabled,
                                       tb, capture_ts, now)
            if msg:
                self.scouts.send(self.rover, msg)
        header = {"node_id": node_id, "seq": seq, "capture_ts": capture_ts,
                  "received_ts": received_ts, "width": width, "height": height,
                  "boxes": boxes, "source": source}
        self.gateway.publish_frame(node_id, header, jpeg)

    # -------------------------------------------------------------- loops
    async def _sim_loop(self) -> None:
        period = 1.0 / self.s.sim_fps
        nxt = time.monotonic()
        while True:
            nxt += period
            now = self.clock.now()
            try:
                if self.sources["ship"] == "sim":
                    jpeg, dets = await asyncio.to_thread(self.sim_ship.frame, now)
                    sh = self.sim_ship
                    self.ingest_frame("ship", jpeg, sh.session_id, sh.seq, now, now, "synced", dets)
                for nid, sc in self.sim_scouts.items():
                    if self.sources[nid] != "sim":
                        continue
                    if nid == self.rover:  # sim rover reaches the person only after the drone's fix
                        ho = self.dispatch_state and self.dispatch_state.get("handoff")
                        launched = bool(ho) and now - ho["ts"] >= 4.0
                    else:
                        launched = self.scenario.launched(nid, now)
                    visible = self.engine.active and launched and not self.scenario.hidden
                    following = self.engine.following(nid)
                    jpeg, dets = await asyncio.to_thread(sc.frame, now, visible, following)
                    self.ingest_frame(nid, jpeg, sc.session_id, sc.seq, now, now, "synced", dets)
            except Exception:  # noqa: BLE001
                log.exception("sim loop")
            await asyncio.sleep(max(0.0, nxt - time.monotonic()))
            if time.monotonic() - nxt > 1.0:
                nxt = time.monotonic()

    async def _state_loop(self) -> None:
        last_drift = 0.0
        while True:
            try:
                self.record(self.engine.tick())
                self.capture.ensure()
                now = self.clock.now()
                fresh = self.engine.any_fresh(now)
                self.sclock.set_fast(self.engine.active and not fresh)
                if now - last_drift >= 1.0:
                    last_drift = now
                    self.drift_view = await asyncio.to_thread(
                        self.drift.update, self.engine.drift_seed(), fresh, self.sclock.sim_at,
                        self.sclock.multiplier, now)
                self.gateway.publish_state(self.state())
            except Exception:  # noqa: BLE001
                log.exception("state loop")
            await asyncio.sleep(0.2)

    def state(self) -> dict:
        snap = self.engine.snapshot()
        now = self.clock.now()
        for nid, n in snap["nodes"].items():
            n["label"] = self.labels.get(nid, nid)
            n["target"] = self.targets.get(nid)
            n["source"] = self.sources.get(nid, "?")
            n["fps"] = round(len(self.fps.get(nid, [])) / 2.0, 1)
            if nid in self.scouts.stats:
                n["link"] = self.scouts.stats[nid]
            n["connected"] = nid in self.scouts.conns if nid != "ship" else None
        snap["drift"] = self.drift_view
        snap["ship"] = {"lat": self.ship.lat, "lon": self.ship.lon, "heading": self.ship.heading_deg,
                        "label": "simulated ship position"}
        snap["rail"] = {"rail_m": self.trigger.rail_m, "armed": self.trigger.armed,
                        "row": self.s.rail_row_frac or None,
                        "persons": [{"track_id": d["track_id"], "z_m": d.get("z_m")}
                                    for d in self.last_ship_dets]}
        snap["aurora"] = {"status": self.aurora.status, "restarts": self.aurora.restarts,
                          **{k: round(v, 1) for k, v in self.aurora.timing.items()}}
        snap["detector"] = type(self.detector).__name__ if self.detector else "none"
        snap["scenario"] = {"multiplier": self.sclock.multiplier, "hidden": self.scenario.hidden}
        snap["outage"] = max(0.0, self.gateway.outage_until - now)
        snap["roles"] = {"drone": self.drone, "rover": self.rover}
        snap["target_label"] = self.s.target_label
        snap["dispatch"] = self.dispatch_state
        snap["capture"] = {"status": self.capture.status, "device": self.capture.opened}
        return snap

    # -------------------------------------------------------------- rover dispatch
    def dispatch_plan(self) -> dict:
        """Where to send the rover. With a fresh ball fix from the deck camera (real relative
        geometry) drive to it; else run out along the deck camera's overboard bearing; else a
        configured default. In every case the rover then searches by camera."""
        b = self.ship_ball
        if b and self.clock.now() - b["ts"] <= 15.0 and b.get("source") == "aurora":
            heading = math.degrees(math.atan2(b["x_m"], b["z_m"]))
            dist = max(0.0, math.hypot(b["x_m"], b["z_m"]) - self.s.dispatch_stop_short_m)
            return {"heading_deg": round(heading, 1), "distance_m": round(dist, 2),
                    "basis": "deck-camera ball fix (real relative)"}
        inc = self.engine.incident
        d = inc.detail if inc else {}
        if d.get("camera") == "aurora" and d.get("z_m"):
            heading = math.degrees(math.atan2(d.get("x_m") or 0.0, d["z_m"]))
            return {"heading_deg": round(heading, 1), "distance_m": self.s.dispatch_distance_m,
                    "basis": "overboard bearing from deck camera (real relative)"}
        return {"heading_deg": self.s.dispatch_heading_deg, "distance_m": self.s.dispatch_distance_m,
                "basis": "default run-out, then camera search"}

    def launch_rover(self) -> None:
        """On man overboard the rover launches with the drone, toward the overboard direction."""
        if not self.engine.active or self.dispatch_state is not None:
            return
        now = self.clock.now()
        plan = self.dispatch_plan()
        self.dispatch_state = {"ts": now, "status": "dispatched", "plan": plan,
                               "node": self.rover, "handoff": None}
        self.scouts.send(self.rover, {"type": "dispatch", **plan})
        self.record([self.engine._ev("dispatch", now, self.rover, **plan)])  # noqa: SLF001

    def handoff_to_rover(self) -> None:
        """After the coordinator confirms the drone's sighting, send that fix to the rover."""
        la = self.engine.last_accepted
        ds = self.dispatch_state
        if not ds or ds.get("handoff") or not la or not la.location or la.node_id == self.rover:
            return
        now = self.clock.now()
        x, y = latlon_to_enu(self.ship.origin, LatLon(la.location.lat, la.location.lon))
        h = {"ts": now, "from_node": la.node_id, "lat": la.location.lat, "lon": la.location.lon,
             "bearing_deg": round(math.degrees(math.atan2(x, y)) % 360, 1),
             "range_m": round(math.hypot(x, y), 1), "provenance": la.location.provenance}
        ds["handoff"] = h
        # the TurboPi keeps its run-out + camera search; the fix is advisory (drone coords are sim)
        self.scouts.send(self.rover, {"type": "handoff", **h})
        self.record([self.engine._ev("handoff", now, self.rover, **h)])  # noqa: SLF001

    def rover_report(self, state: str) -> None:
        if self.dispatch_state is not None:
            self.dispatch_state["status"] = state
            self.dispatch_state["status_ts"] = self.clock.now()

    def forcing_bearing(self) -> float:
        wu, wv, cu, cv = self.forcing.at(0)
        return math.degrees(math.atan2(cu + 0.01 * wu, cv + 0.01 * wv))

    # -------------------------------------------------------------- commands
    async def handle_ws_command(self, msg: dict) -> dict:
        cid = msg.get("command_id") or uuid.uuid4().hex
        try:
            cmd = Command(command_id=cid, type=msg.get("cmd"), args=msg.get("args") or {})
        except Exception as e:  # noqa: BLE001
            return {"command_id": cid, "ok": False, "message": f"bad command: {e.__class__.__name__}"}
        return self.command(cmd)

    def command(self, cmd: Command) -> dict:
        now = self.clock.now()
        t, a = cmd.type, cmd.args
        if t == "manual_mob":
            p = self.ship.camera_point(0.0, self.s.rail_m + 0.5)
            loc = Location(lat=p.lat, lon=p.lon, provenance="simulated", quality="good")
            events = self.engine.open_mob(f"manual:{cmd.command_id}", now, loc, None, "manual")
            if events and events[0]["type"] == "mob":
                self.trigger.fired = True
                if "ship" in self.latest_jpeg:
                    ref = self.save_evidence("ship", "mob-manual.jpg", self.latest_jpeg["ship"])
                    self.engine.incident.mob_image_ref = ref
                    events[0]["image_ref"] = ref
            self.record(events)
            ok = bool(events) and events[0]["type"] == "mob"
            return {"command_id": cmd.command_id, "ok": ok,
                    "message": "incident opened" if ok else "incident already active"}
        if t == "demo_start":
            self.sim_ship.start_crossing(now)
            return {"command_id": cmd.command_id, "ok": True, "message": "sim crew member walks over the rail"}
        if t == "demo_outage":
            self.gateway.start_outage(float(a.get("seconds", 5)))
            return {"command_id": cmd.command_id, "ok": True, "message": "software outage started"}
        if t == "demo_speed":
            self.sclock.set_multiplier(float(a.get("multiplier", 60)))
            return {"command_id": cmd.command_id, "ok": True, "message": f"scenario x{self.sclock.multiplier:g}"}
        if t == "demo_hide":
            self.scenario.hidden = bool(a.get("hidden", True))
            return {"command_id": cmd.command_id, "ok": True,
                    "message": "person hidden from sim scouts" if self.scenario.hidden else "person visible"}
        if t == "demo_inject":
            dist = float(a.get("dist_m", 30))
            la = self.engine.last_accepted
            ref = LatLon(la.location.lat, la.location.lon) if la and la.location else \
                self.scenario.truth_latlon(now)
            if ref is None:
                return {"command_id": cmd.command_id, "ok": False, "message": "no incident"}
            bearing = self.forcing_bearing()
            if self.drift_view:
                c = self.drift_view["centroid"]
                x, y = latlon_to_enu(ref, LatLon(c[0], c[1]))
                if math.hypot(x, y) > 1:
                    bearing = math.degrees(math.atan2(x, y))
            self.scenario.place(ref, bearing, dist, now)
            self.scenario.hidden = False
            return {"command_id": cmd.command_id, "ok": True,
                    "message": f"person reappears {a.get('dist_m', 30)} m downstream"}
        if t == "set_rail":
            if "rail_m" in a:
                self.trigger.rail_m = self.s.rail_m = float(a["rail_m"])
            if "rail_row_frac" in a:
                self.s.rail_row_frac = float(a["rail_row_frac"])
            self.calib_path.write_text(json.dumps({"rail_m": self.s.rail_m,
                                                   "rail_row_frac": self.s.rail_row_frac}))
            return {"command_id": cmd.command_id, "ok": True,
                    "message": f"rail at {self.s.rail_m:.2f} m (depth)"}
        if t == "demo_source":
            node, src = a.get("node"), a.get("source")
            if node in self.sources and src:
                self.sources[node] = src
                return {"command_id": cmd.command_id, "ok": True, "message": f"{node} source = {src}"}
            return {"command_id": cmd.command_id, "ok": False, "message": "bad source"}
        ack, events = self.engine.command(cmd)
        self.record(events)
        return ack.model_dump()


settings = Settings.load()
ground = Ground(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ground.start()
    yield
    await ground.stop()


app = FastAPI(title="Osprey", lifespan=lifespan)


TUNNEL_ALLOWED = ("/scout", "/health")


def via_tunnel(headers) -> bool:
    """Requests that came through the public Cloudflare quick tunnel."""
    host = headers.get("host", "")
    return host.endswith(".trycloudflare.com") or "cf-connecting-ip" in headers


@app.middleware("http")
async def no_cache_static(request, call_next):
    if via_tunnel(request.headers) and request.url.path not in TUNNEL_ALLOWED:
        return JSONResponse({"error": "not available through the tunnel"}, status_code=403)
    resp = await call_next(request)
    if request.url.path.startswith("/static"):
        resp.headers["Cache-Control"] = "no-store"
    return resp
WEB = ROOT / "web"


@app.get("/health")
def health():
    return {"ok": True, "phase": ground.engine.phase(), "sources": ground.sources,
            "server_ts": ground.clock.now()}


BOOT = str(int(time.time()))


@app.get("/")
def index():
    from fastapi.responses import HTMLResponse

    html = (WEB / "index.html").read_text().replace("{{v}}", BOOT)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.get("/scout")
def scout_page():
    return FileResponse(WEB / "scout.html", headers={"Cache-Control": "no-store"})


@app.websocket("/ws/scout")
async def ws_scout(ws: WebSocket, node: str = "B"):
    if node not in ("A", "B"):
        await ws.close()
        return
    await ground.scouts.serve(ws, node)


@app.get("/api/state")
def api_state():
    return JSONResponse(ground.state())


@app.post("/api/commands")
async def api_command(body: dict):
    return await ground.handle_ws_command(body)


@app.get("/api/calibration")
def api_calibration():
    return {"rail_m": ground.trigger.rail_m, "armed": ground.trigger.armed,
            "persons": [{"track_id": d["track_id"], "z_m": d.get("z_m"), "x_m": d.get("x_m"),
                         "bbox": d["bbox"], "confidence": d["confidence"]} for d in ground.last_ship_dets],
            "depth": ground.aurora.depth_at_center(), "intrinsics": ground.aurora.intrinsics,
            "aurora": ground.aurora.status, "timing": ground.aurora.timing}


@app.get("/api/frame/{node_id}.jpg")
def api_frame(node_id: str):
    from fastapi.responses import Response

    jpg = ground.latest_jpeg.get(node_id)
    if jpg is None:
        return JSONResponse({"error": "no frame"}, status_code=404)
    return Response(jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/video_devices")
def api_video_devices():
    return {"devices": list_uvc(), "capture": ground.capture.status}


@app.get("/api/history")
def api_history():
    return ground._history()


@app.websocket("/ws")
async def ws_display(ws: WebSocket):
    if via_tunnel(ws.headers):  # the coordinator display is wired-only
        await ws.close(code=1008)
        return
    await ground.gateway.serve(ws)


app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/evidence", StaticFiles(directory=ground.evidence_dir), name="evidence")
