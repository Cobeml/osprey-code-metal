#!/usr/bin/env python3
"""Measure display-link outage and recovery like the browser does.

Connects to /ws as a display, optionally injects a software outage, treats >1.5 s of silence as
LINK LOST, reconnects every 1 s, and reports: time to LINK LOST, outage length seen, time from
reconnect to first current state, and how much history arrived.
Usage: python3 scripts/measure_outage.py [http://169.254.50.2:8000] [--inject 5] [--watch 60]
  --watch N: don't inject; wait up to N s for a real outage (pull the cable) and measure it.
"""
import argparse
import asyncio
import json
import time
import urllib.request
import uuid

import websockets

LINK_TIMEOUT = 1.5


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://169.254.50.2:8000")
    ap.add_argument("--inject", type=float, default=5.0)
    ap.add_argument("--watch", type=float, default=0.0)
    a = ap.parse_args()
    url = a.base.replace("http", "ws", 1) + "/ws"
    t_lost = t_last = t_inject = None
    ws = await websockets.connect(url, max_size=None, open_timeout=1.5)
    if not a.watch:
        body = json.dumps({"command_id": uuid.uuid4().hex, "cmd": "demo_outage",
                           "args": {"seconds": a.inject}}).encode()
        req = urllib.request.Request(a.base + "/api/commands", body, {"content-type": "application/json"})
        urllib.request.urlopen(req, timeout=3).read()
        t_inject = time.time()
    deadline = time.time() + (a.watch or a.inject + 30)
    t_last = time.time()
    # phase 1: wait for silence
    while time.time() < deadline:
        try:
            await asyncio.wait_for(ws.recv(), timeout=0.1)
            t_last = time.time()
        except asyncio.TimeoutError:
            if time.time() - t_last > LINK_TIMEOUT:
                t_lost = time.time()
                break
        except websockets.ConnectionClosed:
            t_lost = time.time()
            break
    if t_lost is None:
        print("no outage observed")
        return
    print(f"LINK LOST shown {t_lost - t_last:.2f} s after the last message"
          + (f" ({t_lost - t_inject:.2f} s after injection)" if t_inject else ""))
    try:
        await ws.close()
    except Exception:
        pass
    # phase 2: reconnect every 1 s like the browser; measure first state after connect
    while time.time() < deadline:
        t_try = time.time()
        try:
            ws = await websockets.connect(url, max_size=None, open_timeout=1.5)
        except Exception:
            await asyncio.sleep(max(0.0, 1.0 - (time.time() - t_try)))
            continue
        t_conn = time.time()
        try:
            first = json.loads(await asyncio.wait_for(ws.recv(), timeout=LINK_TIMEOUT * 4))
        except Exception:
            await ws.close()
            continue
        t_state = time.time()
        hist = None
        while hist is None and time.time() - t_state < 5:
            m = await ws.recv()
            if isinstance(m, str) and json.loads(m).get("type") == "history":
                hist = json.loads(m)
        t_hist = time.time()
        print(f"gap (last message -> current state) {t_state - t_last:.2f} s")
        print(f"reconnect -> current state {t_state - t_conn:.3f} s ({first['type']}, phase {first.get('phase')})")
        print(f"current state -> history {t_hist - t_state:.3f} s, {len(hist['events']) if hist else 0} events")
        if t_inject:
            print(f"recovery after outage end: {t_state - (t_inject + a.inject):.2f} s")
        await ws.close()
        return


asyncio.run(main())
