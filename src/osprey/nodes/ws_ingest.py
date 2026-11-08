"""Scout WebSocket ingest (phone page or TurboPi client), through the Cloudflare tunnel.

Binary frames: uint32 LE header_len | header JSON | JPEG, header {node_id, session_id, seq,
capture_ts_ms (sender clock), width, height}. Clock sync: the sender sends {"ping": t_ms}; we answer
{"pong": t_ms, "srv": server_ms}; the sender reports {"sync": t_ms, "srv": server_ms, "recv": t_ms2}.
Frames go into a latest-only slot per node; one worker per node detects, tracks and ingests.
Back to the sender: {"type":"status", ...} twice a second and {"type":"follow"|"hold"|"stop"} for
Scout A (follow.py).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from ..clock import OffsetEstimator
from ..gateway import unpack_frame
from ..perception.tracker import IoUTracker

log = logging.getLogger("osprey.ws")


class _Conn:
    def __init__(self, ws: WebSocket, node_id: str):
        self.ws = ws
        self.node_id = node_id
        self.session_id: Optional[str] = None
        self.offset = OffsetEstimator()
        self.out: list[dict] = []
        self.wake = asyncio.Event()


class ScoutIngest:
    def __init__(self, ground):
        self.g = ground
        self.slots: dict[str, tuple] = {}
        self.events: dict[str, asyncio.Event] = {}
        self.trackers: dict[str, IoUTracker] = {}
        self.conns: dict[str, _Conn] = {}
        self.stats: dict[str, dict] = {}

    def start(self, nodes=("A", "B")) -> list[asyncio.Task]:
        return [asyncio.create_task(self._worker(n)) for n in nodes]

    def send(self, node_id: str, msg: dict) -> None:
        c = self.conns.get(node_id)
        if c is not None:
            c.out.append(msg)
            c.wake.set()

    async def serve(self, ws: WebSocket, node_id: str) -> None:
        await ws.accept()
        c = _Conn(ws, node_id)
        old = self.conns.get(node_id)
        self.conns[node_id] = c
        if old is not None:
            try:
                await old.ws.close()
            except Exception:  # noqa: BLE001
                pass
        sender = asyncio.create_task(self._sender(c))
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                now = time.time()
                if msg.get("bytes"):
                    hdr, jpeg = unpack_frame(msg["bytes"])
                    if hdr.get("session_id") != c.session_id:
                        c.session_id = hdr.get("session_id")
                        c.offset = OffsetEstimator()
                    if self.g.sources.get(node_id) != "ws":
                        self.g.sources[node_id] = "ws"  # a real scout takes over its node
                    self.slots[node_id] = (hdr, jpeg, now, c)
                    self.events.setdefault(node_id, asyncio.Event()).set()
                elif msg.get("text"):
                    m = json.loads(msg["text"])
                    if "ping" in m:
                        c.out.append({"pong": m["ping"], "srv": now * 1000})
                        c.wake.set()
                    elif "sync" in m:
                        c.offset.add(m["sync"] / 1000, m["srv"] / 1000, m["recv"] / 1000)
                    elif m.get("type") == "rover_state" and node_id == self.g.rover:
                        ob = m.get("onboard")
                        self.g.rover_report(str(m.get("state", "")),
                                            ob if isinstance(ob, dict) else None)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            sender.cancel()
            if self.conns.get(node_id) is c:
                del self.conns[node_id]

    async def _sender(self, c: _Conn) -> None:
        try:
            while True:
                try:
                    await asyncio.wait_for(c.wake.wait(), 0.5)
                except asyncio.TimeoutError:
                    pass
                c.wake.clear()
                msgs, c.out = c.out, []
                msgs.append(self._status(c))
                for m in msgs:
                    await c.ws.send_text(json.dumps(m))
        except Exception:  # noqa: BLE001
            pass

    def _status(self, c: _Conn) -> dict:
        snap_node = self.g.engine.nodes.get(c.node_id)
        pill = self.g.engine.node_pill(snap_node, time.time()) if snap_node else "?"
        st = self.stats.get(c.node_id, {})
        return {"type": "status", "phase": self.g.engine.phase(), "pill": pill,
                "following": self.g.engine.following(c.node_id), "clock": c.offset.quality,
                "rtt_ms": round((c.offset.rtt or 0) * 1000), "proc_fps": st.get("fps"),
                "detect_ms": st.get("detect_ms")}

    async def _worker(self, node_id: str) -> None:
        ev = self.events.setdefault(node_id, asyncio.Event())
        tracker = self.trackers.setdefault(node_id, IoUTracker())
        times: list[float] = []
        while True:
            await ev.wait()
            ev.clear()
            slot = self.slots.pop(node_id, None)
            if slot is None or self.g.sources.get(node_id) != "ws":
                continue
            hdr, jpeg, received, c = slot
            try:
                dets, ms = await asyncio.to_thread(self._detect, node_id, jpeg)
                capture = c.offset.to_server(hdr["capture_ts_ms"] / 1000.0, received)
                dets = tracker.update(capture, dets)
                self.g.ingest_frame(node_id, jpeg, hdr["session_id"], int(hdr["seq"]), capture,
                                    received, c.offset.quality, dets, hdr.get("width", 640),
                                    hdr.get("height", 480), "ws")
                now = time.time()
                times.append(now)
                times[:] = [t for t in times if now - t <= 2.0]
                self.stats[node_id] = {"fps": round(len(times) / 2.0, 1), "detect_ms": round(ms, 1),
                                       "latency_ms": round((now - capture) * 1000)}
            except Exception:  # noqa: BLE001
                log.exception("scout worker %s", node_id)

    def _detect(self, node_id: str, jpeg: bytes) -> tuple[list[dict], float]:
        try:
            import cv2
            import numpy as np
        except ImportError:
            return [], 0.0
        t0 = time.perf_counter()
        bgr = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        dets = self.g.detect(node_id, bgr)
        return dets, (time.perf_counter() - t0) * 1000
