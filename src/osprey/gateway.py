"""Coordinator gateway: the ONLY path from the ground processor to the display (FR-10).

Per connected display: snapshot first (state + latest frame per node), then history in capture
order flagged history=true, then live state/events/frames. Frames are latest-only per node and
dropped when the socket is slow. The outage injector silences this path only; ground processing,
retention and following are untouched.
"""
from __future__ import annotations

import asyncio
import json
import struct
from typing import Callable, Optional

from fastapi import WebSocket, WebSocketDisconnect

from .clock import Clock

HEARTBEAT_S = 0.5


def pack_frame(header: dict, jpeg: bytes) -> bytes:
    h = json.dumps(header, separators=(",", ":")).encode()
    return struct.pack("<I", len(h)) + h + jpeg


def unpack_frame(buf: bytes) -> tuple[dict, bytes]:
    (n,) = struct.unpack_from("<I", buf, 0)
    return json.loads(buf[4:4 + n]), buf[4 + n:]


class Thinner:
    """Forward at most one routine 'same track' accepted observation per node per second."""

    def __init__(self, period: float = 1.0):
        self.period = period
        self.last: dict[str, float] = {}

    def keep(self, e: dict) -> bool:
        if e.get("type") != "observation" or e.get("kind") != "accepted" or e.get("reason") != "same track":
            return True
        n = e.get("node_id")
        if e["capture_ts"] - self.last.get(n, -1e9) >= self.period:
            self.last[n] = e["capture_ts"]
            return True
        return False


class _Client:
    def __init__(self, ws: WebSocket, read_only: bool = False):
        self.ws = ws
        self.read_only = read_only
        self.frames: dict[str, bytes] = {}
        self.events: list[dict] = []
        self.state: Optional[dict] = None
        self.acks: list[dict] = []
        self.wake = asyncio.Event()
        self.thin = Thinner()


class Gateway:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.clients: set[_Client] = set()
        self.latest_frames: dict[str, bytes] = {}
        self.latest_state: Optional[dict] = None
        self.outage_until = 0.0
        self.history_fn: Callable[[], list[dict]] = lambda: []
        self.command_fn: Optional[Callable] = None
        self.stats = {"connects": 0}

    @property
    def in_outage(self) -> bool:
        return self.clock.now() < self.outage_until

    def start_outage(self, seconds: float) -> None:
        self.outage_until = self.clock.now() + seconds

    # -------------------------------------------------------------- publish (ground side)
    def publish_state(self, state: dict) -> None:
        self.latest_state = state
        for c in self.clients:
            c.state = state
            c.wake.set()

    def publish_event(self, e: dict) -> None:
        for c in self.clients:
            if c.thin.keep(e):
                c.events.append(e)
                c.wake.set()

    def publish_frame(self, node_id: str, header: dict, jpeg: bytes) -> None:
        buf = pack_frame(header, jpeg)
        self.latest_frames[node_id] = buf
        for c in self.clients:
            c.frames[node_id] = buf  # latest-only: overwrite unsent frame
            c.wake.set()

    # -------------------------------------------------------------- per-display connection
    async def serve(self, ws: WebSocket, read_only: bool = False) -> None:
        await ws.accept()
        c = _Client(ws, read_only)
        while self.in_outage:  # injected outage: a new connection gets nothing either
            await asyncio.sleep(0.1)
        self.clients.add(c)
        self.stats["connects"] += 1
        recv = asyncio.create_task(self._receive(c))
        try:
            # 1) current state and live video first
            if self.latest_state:
                await ws.send_text(json.dumps({"type": "state", **self.latest_state}))
            for buf in list(self.latest_frames.values()):
                await ws.send_bytes(buf)
            # 2) then backlog, capture-time order, flagged as history
            thin = Thinner()
            hist = [e for e in self.history_fn() if thin.keep(e)]
            await ws.send_text(json.dumps({"type": "history", "history": True, "events": hist},
                                          default=str))
            c.events = []
            # 3) live
            while True:
                try:
                    await asyncio.wait_for(c.wake.wait(), HEARTBEAT_S)
                except asyncio.TimeoutError:
                    pass
                c.wake.clear()
                while c.acks:
                    await ws.send_text(json.dumps({"type": "ack", **c.acks.pop(0)}))
                if self.in_outage:
                    c.frames.clear()
                    c.events.clear()
                    c.state = None
                    continue
                sent = False
                if c.state is not None:
                    st, c.state = c.state, None
                    await ws.send_text(json.dumps({"type": "state", **st}, default=str))
                    sent = True
                if c.events:
                    ev, c.events = c.events, []
                    await ws.send_text(json.dumps({"type": "events", "events": ev}, default=str))
                    sent = True
                for node in list(c.frames):
                    buf = c.frames.pop(node, None)
                    if buf is not None:
                        await ws.send_bytes(buf)
                        sent = True
                if not sent:
                    await ws.send_text(json.dumps({"type": "hb", "server_ts": self.clock.now()}))
        except (WebSocketDisconnect, RuntimeError, ConnectionError):
            pass
        finally:
            self.clients.discard(c)
            recv.cancel()

    async def _receive(self, c: _Client) -> None:
        try:
            while True:
                msg = json.loads(await c.ws.receive_text())
                if self.in_outage:
                    continue  # link is down both ways
                if msg.get("type") == "command" and c.read_only:
                    c.acks.append({"command_id": msg.get("command_id"), "ok": False,
                                   "message": "view-only screen: commands are refused"})
                    c.wake.set()
                elif msg.get("type") == "command" and self.command_fn:
                    c.acks.append(await self.command_fn(msg))
                    c.wake.set()
        except Exception:  # noqa: BLE001 - disconnect ends the receiver
            pass
