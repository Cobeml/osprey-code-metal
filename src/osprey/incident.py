"""Incident state machine: phases, confirmation, association/reacquisition, freshness, end.

Pure logic: no IO. Callers feed FrameReports, commands and ticks, persist the returned events,
and publish snapshots. All times are server-clock seconds.

Association rules (FR-09), horizontal distance, inclusive 50.0 m:
  * first candidate of the incident            -> coordinator confirms
  * a node's first association (another node already accepted)
        reference = most recent accepted location from any node; <= 50 m auto, else confirm
  * reacquisition after this node's visual loss
        reference = this node's last accepted location before the loss; <= 50 m auto, else confirm
  * missing or unreliable location (either side) -> confirm
  * while a node is tracking, its confirmed track id continues automatically; another track
    within 50 m of the node's last sighting is treated as an id switch.
Multiple simultaneous detections on one node: they are evaluated in descending confidence, the
highest-confidence feasible one is associated, and every other detection is shown as a candidate.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .clock import Clock
from .contracts import Ack, Command, Detection, FrameReport, Location, Observation, Phase
from .geo import LatLon, horizontal_distance_m

FRESH_S = 6.0          # sighting freshness (PRD): stale when age > 6.0 s; exactly 6.0 is fresh
VISUAL_LOSS_S = 1.5    # node visual contact lost when no accepted sighting for this long
INPUT_LOSS_S = 2.0     # node video input lost when no frame for this long
CANDIDATE_TTL_S = 6.0  # candidates without updates expire after this long
ASSOC_RADIUS_M = 50.0


def is_fresh(capture_ts: float, now: float) -> bool:
    return (now - capture_ts) <= FRESH_S


def within_radius(ref: Optional[Location], loc: Optional[Location]) -> tuple[bool, Optional[float]]:
    if ref is None or loc is None or not ref.usable or not loc.usable:
        return False, None
    d = horizontal_distance_m(LatLon(ref.lat, ref.lon), LatLon(loc.lat, loc.lon))
    d = round(d, 3)  # mm resolution so the inclusive 50.0 m boundary survives float round-trips
    return d <= ASSOC_RADIUS_M, d


@dataclass
class Sighting:
    event_id: str
    node_id: str
    session_id: str
    seq: int
    capture_ts: float
    track_id: int
    bbox: tuple
    confidence: float
    location: Optional[Location]
    image_ref: Optional[str]

    def public(self) -> dict:
        return {
            "event_id": self.event_id, "node_id": self.node_id, "capture_ts": self.capture_ts,
            "track_id": self.track_id, "bbox": list(self.bbox), "confidence": self.confidence,
            "location": self.location.model_dump() if self.location else None,
            "image_ref": self.image_ref,
        }


@dataclass
class Candidate:
    candidate_id: str
    sighting: Sighting
    first_ts: float
    reason: str
    distance_m: Optional[float]


@dataclass
class NodeState:
    node_id: str
    session_id: Optional[str] = None
    sessions_seen: set = field(default_factory=set)
    last_seq: int = -1
    last_capture_ts: Optional[float] = None
    input_lost: bool = False
    clock_quality: str = "unknown"
    last_image_ref: Optional[str] = None
    # per-incident
    has_target: bool = False
    lost: bool = False
    lost_ts: Optional[float] = None
    target_track: Optional[int] = None
    last_accepted: Optional[Sighting] = None
    loss_reference: Optional[Sighting] = None
    candidates: dict = field(default_factory=dict)
    rejected: set = field(default_factory=set)

    def reset_incident(self) -> None:
        self.has_target = False
        self.lost = False
        self.lost_ts = None
        self.target_track = None
        self.last_accepted = None
        self.loss_reference = None
        self.candidates = {}
        self.rejected = set()


@dataclass
class Incident:
    incident_id: str
    opened_ts: float
    mob_capture_ts: float
    mob_location: Optional[Location]
    mob_image_ref: Optional[str]
    source: str
    detail: dict = field(default_factory=dict)
    first_contact_ts: Optional[float] = None
    ended: bool = False
    ended_ts: Optional[float] = None


def default_incident_id(ts: float) -> str:
    return "INC-" + time.strftime("%H%M%S", time.localtime(ts)) + f"-{int(ts * 1000) % 1000:03d}"


class IncidentEngine:
    def __init__(self, clock: Clock, node_ids=("ship", "A", "B"),
                 id_factory: Callable[[float], str] = default_incident_id):
        self.clock = clock
        self.id_factory = id_factory
        self.nodes: dict[str, NodeState] = {n: NodeState(n) for n in node_ids}
        self.incident: Optional[Incident] = None
        self.follow_enabled = True
        self.last_accepted: Optional[Sighting] = None  # most recent by capture_ts, any node
        self._seen: set[str] = set()
        self._acks: dict[str, Ack] = {}
        self._counter = itertools.count(1)

    # ------------------------------------------------------------------ helpers
    @property
    def active(self) -> bool:
        return self.incident is not None and not self.incident.ended

    @property
    def armed(self) -> bool:
        return not self.active

    def _iid(self) -> Optional[str]:
        return self.incident.incident_id if self.incident else None

    def _ev(self, type_: str, capture_ts: float, node_id: Optional[str] = None,
            event_id: Optional[str] = None, **payload) -> dict:
        eid = event_id or f"{type_}:{self._iid() or 'none'}:{next(self._counter)}:{int(self.clock.now()*1000)}"
        return {"event_id": eid, "type": type_, "incident_id": self._iid(), "node_id": node_id,
                "capture_ts": capture_ts, "recorded_ts": self.clock.now(), **payload}

    def _node(self, node_id: str) -> NodeState:
        if node_id not in self.nodes:
            self.nodes[node_id] = NodeState(node_id)
        return self.nodes[node_id]

    # ------------------------------------------------------------------ MOB
    def open_mob(self, event_id: str, capture_ts: float, location: Optional[Location],
                 image_ref: Optional[str], source: str, detail: Optional[dict] = None) -> list[dict]:
        """Open an incident (FR-01). Exactly one per arming: ignored while an incident is active."""
        if event_id in self._seen:
            return []
        self._seen.add(event_id)
        if self.active:
            return [self._ev("mob_ignored", capture_ts, event_id=f"ignored:{event_id}",
                             source=source, reason="incident already active")]
        now = self.clock.now()
        self.incident = Incident(self.id_factory(now), now, capture_ts, location, image_ref,
                                 source, detail or {})
        self.last_accepted = None
        self.follow_enabled = True
        for n in self.nodes.values():
            n.reset_incident()
        return [self._ev("mob", capture_ts, node_id="ship" if source == "shipcam" else None,
                         event_id=event_id, source=source,
                         location=location.model_dump() if location else None,
                         image_ref=image_ref, detail=detail or {})]

    # ------------------------------------------------------------------ frames
    def ingest(self, r: FrameReport) -> list[dict]:
        eid = r.event_id
        if eid in self._seen:
            return []  # duplicate delivery: no effect at all
        self._seen.add(eid)
        node = self._node(r.node_id)
        events: list[dict] = []

        if r.session_id != node.session_id:
            if r.session_id in node.sessions_seen:
                return self._archive_late(r, "old session")
            node.sessions_seen.add(r.session_id)
            if node.session_id is not None:
                events.append(self._ev("session_restart", r.capture_ts, r.node_id,
                                       old=node.session_id, new=r.session_id))
                if node.has_target and not node.lost:
                    events += self._mark_lost(node, r.capture_ts, "source restarted")
                node.target_track = None
                node.candidates = {}
            node.session_id = r.session_id
            node.last_seq = -1

        if r.seq <= node.last_seq or (node.last_capture_ts is not None
                                      and r.capture_ts < node.last_capture_ts):
            return events + self._archive_late(r, "out of order")

        node.last_seq = r.seq
        node.last_capture_ts = r.capture_ts
        node.clock_quality = r.clock_quality
        if r.image_ref:
            node.last_image_ref = r.image_ref
        if node.input_lost:
            node.input_lost = False
            events.append(self._ev("input_restored", r.capture_ts, r.node_id))

        if self.incident is None or r.node_id == "ship":
            return events
        if self.incident.ended:
            if r.detections:
                events += self._archive_late(r, "after end")
            return events

        # visual loss is judged in capture time, so late-but-ordered frames are handled right
        if node.has_target and not node.lost and node.last_accepted and \
                r.capture_ts - node.last_accepted.capture_ts > VISUAL_LOSS_S:
            events += self._mark_lost(node, node.last_accepted.capture_ts + VISUAL_LOSS_S,
                                      "no sighting")

        associated = False
        for d in sorted(r.detections, key=lambda d: -d.confidence):
            s = Sighting(f"{eid}:{d.track_id}", r.node_id, r.session_id, r.seq, r.capture_ts,
                         d.track_id, tuple(d.bbox), d.confidence, d.location, r.image_ref)
            cid = f"{r.node_id}:{r.session_id}:{d.track_id}"
            if not associated:
                ok, reason, dist = self._decide(node, d)
                if ok:
                    events += self._accept(node, s, reason, dist)
                    node.candidates.pop(cid, None)
                    associated = True
                    continue
            else:
                _, reason, dist = False, "another detection on this node was associated", None
            if cid in node.rejected:
                continue
            events += self._candidate(node, cid, s, reason, dist)
        return events

    def _decide(self, node: NodeState, d: Detection) -> tuple[bool, str, Optional[float]]:
        if node.has_target and not node.lost:
            if d.track_id == node.target_track:
                return True, "same track", None
            ok, dist = within_radius(node.last_accepted.location if node.last_accepted else None,
                                     d.location)
            if ok:
                return True, "track switch within 50 m of this node's last sighting", dist
            return False, "second person on a tracking node", dist
        if node.has_target and node.lost:
            ref = node.loss_reference
            ok, dist = within_radius(ref.location if ref else None, d.location)
            if ok:
                return True, "reacquired within 50 m of this node's last sighting", dist
            if dist is None:
                return False, "reacquisition without usable location", None
            return False, f"reacquisition {dist:.0f} m from this node's last sighting (> 50 m)", dist
        if self.last_accepted is None:
            return False, "first sighting of this incident needs confirmation", None
        ok, dist = within_radius(self.last_accepted.location, d.location)
        if ok:
            return True, "within 50 m of the latest accepted sighting", dist
        if dist is None:
            return False, "no usable location to associate", None
        return False, f"{dist:.0f} m from the latest accepted sighting (> 50 m)", dist

    def _accept(self, node: NodeState, s: Sighting, reason: str, dist: Optional[float],
                by: str = "auto") -> list[dict]:
        events = []
        if node.lost:
            events.append(self._ev("reacquired", s.capture_ts, node.node_id, reason=reason,
                                   by=by, distance_m=dist))
        elif not node.has_target:
            events.append(self._ev("associated", s.capture_ts, node.node_id, reason=reason,
                                   by=by, distance_m=dist))
        node.has_target = True
        node.lost = False
        node.lost_ts = None
        node.target_track = s.track_id
        node.last_accepted = s
        node.loss_reference = None
        if self.last_accepted is None or s.capture_ts >= self.last_accepted.capture_ts:
            self.last_accepted = s
        if self.incident.first_contact_ts is None:
            self.incident.first_contact_ts = s.capture_ts
        events.append(self._obs_event(s, "accepted", reason, dist))
        return events

    def _candidate(self, node: NodeState, cid: str, s: Sighting, reason: str,
                   dist: Optional[float]) -> list[dict]:
        c = node.candidates.get(cid)
        if c is not None:
            c.sighting, c.reason, c.distance_m = s, reason, dist
            return []
        node.candidates[cid] = Candidate(cid, s, s.capture_ts, reason, dist)
        return [self._obs_event(s, "candidate", reason, dist, candidate_id=cid)]

    def _obs_event(self, s: Sighting, kind: str, reason: str, dist: Optional[float],
                   candidate_id: Optional[str] = None) -> dict:
        obs = Observation(
            event_id=f"{s.event_id}:{kind}", incident_id=self._iid(), node_id=s.node_id,
            session_id=s.session_id, seq=s.seq, capture_ts=s.capture_ts,
            received_ts=self.clock.now(), kind=kind, track_id=s.track_id,
            target_id=self._iid() if kind == "accepted" else None, candidate_id=candidate_id,
            bbox=s.bbox, confidence=s.confidence, image_ref=s.image_ref, location=s.location,
            reason=reason,
        )
        ev = obs.model_dump()
        ev.update(type="observation", recorded_ts=self.clock.now(), distance_m=dist)
        return ev

    def _mark_lost(self, node: NodeState, at_ts: float, why: str) -> list[dict]:
        node.lost = True
        node.lost_ts = at_ts
        node.loss_reference = node.last_accepted
        node.target_track = None
        return [self._ev("lost", at_ts, node.node_id, reason=why,
                         last_sighting=node.last_accepted.public() if node.last_accepted else None)]

    def _archive_late(self, r: FrameReport, why: str) -> list[dict]:
        if not r.detections:
            return []
        return [self._ev("late", r.capture_ts, r.node_id, event_id=f"late:{r.event_id}",
                         reason=why, session_id=r.session_id, seq=r.seq,
                         detections=[d.model_dump() for d in r.detections])]

    # ------------------------------------------------------------------ time
    def tick(self) -> list[dict]:
        now = self.clock.now()
        events: list[dict] = []
        for node in self.nodes.values():
            if node.last_capture_ts is not None and not node.input_lost and \
                    now - node.last_capture_ts > INPUT_LOSS_S:
                node.input_lost = True
                events.append(self._ev("input_lost", node.last_capture_ts + INPUT_LOSS_S,
                                       node.node_id))
            if not self.active:
                continue
            if node.has_target and not node.lost and node.last_accepted and \
                    now - node.last_accepted.capture_ts > VISUAL_LOSS_S:
                events += self._mark_lost(node, node.last_accepted.capture_ts + VISUAL_LOSS_S,
                                          "video input lost" if node.input_lost else "no sighting")
            for cid in [c for c, v in node.candidates.items()
                        if now - v.sighting.capture_ts > CANDIDATE_TTL_S]:
                del node.candidates[cid]
        return events

    def any_fresh(self, now: Optional[float] = None) -> bool:
        now = self.clock.now() if now is None else now
        return any(n.last_accepted is not None and is_fresh(n.last_accepted.capture_ts, now)
                   for n in self.nodes.values())

    def phase(self, now: Optional[float] = None) -> Phase:
        now = self.clock.now() if now is None else now
        if self.incident is None:
            return "STANDBY"
        if self.incident.ended:
            return "ENDED"
        if any(n.has_target and not n.lost and n.last_accepted
               and is_fresh(n.last_accepted.capture_ts, now) for n in self.nodes.values()):
            return "TRACKING"
        if any(n.candidates for n in self.nodes.values()):
            return "CANDIDATE"
        if self.any_fresh(now):
            return "TRACKING"  # visual lost < 6 s ago: the last fix is still fresh
        if self.last_accepted is not None:
            return "CONTACT_LOST"
        return "OVERBOARD"

    def node_pill(self, node: NodeState, now: float) -> str:
        if node.last_capture_ts is None or node.input_lost or now - node.last_capture_ts > INPUT_LOSS_S:
            return "NO VIDEO"
        if not self.active or node.node_id == "ship":
            return "LIVE"
        if node.candidates:
            return "CANDIDATE"
        if node.has_target and not node.lost:
            return "TRACKING"
        if node.has_target:
            return "CONTACT LOST"
        return "LIVE"

    def following(self, node_id: str = "A") -> bool:
        n = self.nodes.get(node_id)
        return bool(self.active and self.follow_enabled and n and n.has_target and not n.lost)

    def drift_seed(self) -> Optional[dict]:
        """Where drift should start: latest accepted sighting, else the overboard point."""
        if not self.active:
            return None
        if self.last_accepted is not None and self.last_accepted.location is not None:
            return {"kind": "sighting", "ts": self.last_accepted.capture_ts,
                    "location": self.last_accepted.location, "node_id": self.last_accepted.node_id}
        if self.incident.mob_location is not None:
            return {"kind": "overboard", "ts": self.incident.mob_capture_ts,
                    "location": self.incident.mob_location, "node_id": "ship"}
        return None

    # ------------------------------------------------------------------ commands
    def command(self, cmd: Command) -> tuple[Ack, list[dict]]:
        if cmd.command_id in self._acks:
            a = self._acks[cmd.command_id].model_copy(update={"duplicate": True})
            return a, []
        ack, events = self._run(cmd)
        self._acks[cmd.command_id] = ack
        return ack, events

    def _find_candidate(self, cid: str) -> tuple[Optional[NodeState], Optional[Candidate]]:
        for n in self.nodes.values():
            if cid in n.candidates:
                return n, n.candidates[cid]
        return None, None

    def _run(self, cmd: Command) -> tuple[Ack, list[dict]]:
        now = self.clock.now()
        t = cmd.type
        if t == "end_incident":
            if self.incident is None:
                return Ack(command_id=cmd.command_id, ok=False, message="no incident"), []
            if self.incident.ended:
                return Ack(command_id=cmd.command_id, ok=True, message="already ended"), []
            self.incident.ended = True
            self.incident.ended_ts = now
            self.follow_enabled = False
            for n in self.nodes.values():
                n.candidates = {}
            return (Ack(command_id=cmd.command_id, ok=True, message="incident ended"),
                    [self._ev("end", now, by="coordinator", command_id=cmd.command_id)])
        if not self.active:
            return Ack(command_id=cmd.command_id, ok=False, message="no active incident"), []
        if t == "confirm":
            cid = cmd.args.get("candidate_id", "")
            node, c = self._find_candidate(cid)
            if c is None:
                return Ack(command_id=cmd.command_id, ok=False, message="candidate expired"), []
            node.candidates.pop(cid)
            events = [self._ev("confirm", now, node.node_id, candidate_id=cid,
                               command_id=cmd.command_id)]
            events += self._accept(node, c.sighting, "confirmed by coordinator", c.distance_m,
                                   by="coordinator")
            return Ack(command_id=cmd.command_id, ok=True, message=f"tracking on {node.node_id}"), events
        if t == "reject":
            cid = cmd.args.get("candidate_id", "")
            node, c = self._find_candidate(cid)
            if c is None:
                return Ack(command_id=cmd.command_id, ok=False, message="candidate expired"), []
            node.candidates.pop(cid)
            node.rejected.add(cid)
            return (Ack(command_id=cmd.command_id, ok=True, message="candidate rejected"),
                    [self._ev("reject", now, node.node_id, candidate_id=cid)])
        if t in ("stop_follow", "resume_follow"):
            self.follow_enabled = t == "resume_follow"
            return (Ack(command_id=cmd.command_id, ok=True,
                        message="following resumed" if self.follow_enabled else "following stopped"),
                    [self._ev(t, now, "A", command_id=cmd.command_id)])
        return Ack(command_id=cmd.command_id, ok=False, message=f"unknown command {t}"), []

    # ------------------------------------------------------------------ snapshot
    def snapshot(self) -> dict:
        now = self.clock.now()
        inc = self.incident
        nodes = {}
        for n in self.nodes.values():
            la = n.last_accepted
            nodes[n.node_id] = {
                "pill": self.node_pill(n, now),
                "session_id": n.session_id,
                "last_capture_ts": n.last_capture_ts,
                "clock_quality": n.clock_quality,
                "has_target": n.has_target,
                "lost": n.lost,
                "lost_ts": n.lost_ts,
                "last_accepted": la.public() if la else None,
                "fresh": bool(la and is_fresh(la.capture_ts, now)),
                "candidates": [
                    {"candidate_id": c.candidate_id, "reason": c.reason, "distance_m": c.distance_m,
                     "first_ts": c.first_ts, **c.sighting.public()}
                    for c in n.candidates.values()
                ],
                "last_image_ref": n.last_image_ref,
            }
        return {
            "server_ts": now,
            "phase": self.phase(now),
            "armed": self.armed,
            "follow_enabled": self.follow_enabled,
            "following": self.following("A"),
            "incident": None if inc is None else {
                "incident_id": inc.incident_id, "opened_ts": inc.opened_ts,
                "mob_capture_ts": inc.mob_capture_ts, "source": inc.source,
                "mob_location": inc.mob_location.model_dump() if inc.mob_location else None,
                "mob_image_ref": inc.mob_image_ref, "detail": inc.detail,
                "first_contact_ts": inc.first_contact_ts, "ended": inc.ended,
                "ended_ts": inc.ended_ts,
            },
            "last_accepted": self.last_accepted.public() if self.last_accepted else None,
            "nodes": nodes,
        }
