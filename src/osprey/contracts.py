"""Data contracts shared by the ground processor, the gateway and the UI (FR-02)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Provenance = Literal["real_relative", "simulated", "none"]
Quality = Literal["good", "degraded", "unreliable"]
ClockQuality = Literal["synced", "estimated", "unknown"]
ObsKind = Literal["candidate", "accepted", "lost", "input_lost"]
Phase = Literal["STANDBY", "OVERBOARD", "CANDIDATE", "TRACKING", "CONTACT_LOST", "ENDED"]


class Location(BaseModel):
    lat: float
    lon: float
    provenance: Provenance = "simulated"
    quality: Quality = "good"
    accuracy_m: Optional[float] = None

    @property
    def usable(self) -> bool:
        """Locations that may be used for automatic association (FR-09)."""
        return self.provenance != "none" and self.quality != "unreliable"


class Detection(BaseModel):
    """One person detection in one frame, after tracking."""

    track_id: int
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2, normalized 0..1
    confidence: float
    location: Optional[Location] = None


class FrameReport(BaseModel):
    """What a node pipeline hands the incident engine for each processed frame."""

    node_id: str
    session_id: str
    seq: int
    capture_ts: float  # server clock domain
    received_ts: float
    clock_quality: ClockQuality = "unknown"
    detections: list[Detection] = Field(default_factory=list)
    image_ref: Optional[str] = None

    @property
    def event_id(self) -> str:
        return f"{self.node_id}:{self.session_id}:{self.seq}"


class Observation(BaseModel):
    event_id: str
    incident_id: Optional[str]
    node_id: str
    session_id: str
    seq: int
    capture_ts: float
    received_ts: float
    kind: ObsKind
    track_id: Optional[int] = None
    target_id: Optional[str] = None
    candidate_id: Optional[str] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    confidence: Optional[float] = None
    image_ref: Optional[str] = None
    location: Optional[Location] = None
    reason: Optional[str] = None  # why it was a candidate / accepted (association rule)


class Command(BaseModel):
    command_id: str
    type: Literal[
        "confirm", "reject", "stop_follow", "resume_follow", "end_incident", "manual_mob",
        "demo_outage", "demo_speed", "demo_inject", "demo_source", "demo_hide", "demo_reset", "demo_start", "set_rail",
    ]
    args: dict = Field(default_factory=dict)


class Ack(BaseModel):
    command_id: str
    ok: bool
    message: str = ""
    duplicate: bool = False
