#!/usr/bin/env python3
"""Stream synthetic frames as a scout through the tunnel and report what the ground measured.
Usage: python3 scripts/fake_scout.py https://<x>.trycloudflare.com [node=B] [seconds=10]"""
import asyncio
import io
import json
import struct
import sys
import time

import websockets
from PIL import Image, ImageDraw

URL = sys.argv[1].rstrip("/")
NODE = sys.argv[2] if len(sys.argv) > 2 else "B"
SECS = float(sys.argv[3]) if len(sys.argv) > 3 else 10


def jpeg(i):
    img = Image.new("RGB", (640, 480), (20, 70, 105))
    ImageDraw.Draw(img).text((20, 20), f"fake scout frame {i}", fill=(255, 255, 0))
    b = io.BytesIO()
    img.save(b, "JPEG", quality=70)
    return b.getvalue()


async def main():
    ws_url = URL.replace("https://", "wss://").replace("http://", "ws://") + f"/ws/scout?node={NODE}"
    frames = [jpeg(i) for i in range(10)]
    last = {}
    async with websockets.connect(ws_url, max_size=None) as ws:
        async def rx():
            async for m in ws:
                d = json.loads(m)
                if "pong" in d:
                    await ws.send(json.dumps({"sync": d["pong"], "srv": d["srv"], "recv": time.time() * 1000}))
                elif d.get("type") == "status":
                    last.update(d)
        t = asyncio.create_task(rx())
        t0, seq = time.time(), 0
        while time.time() - t0 < SECS:
            if seq % 10 == 0:
                await ws.send(json.dumps({"ping": time.time() * 1000}))
            seq += 1
            h = json.dumps({"node_id": NODE, "session_id": "fake1", "seq": seq,
                            "capture_ts_ms": time.time() * 1000, "width": 640, "height": 480}).encode()
            await ws.send(struct.pack("<I", len(h)) + h + frames[seq % 10])
            await asyncio.sleep(0.1)
        await asyncio.sleep(1)
        t.cancel()
    print(f"sent {seq} frames in {SECS:.0f} s; ground status: {last}")


asyncio.run(main())
