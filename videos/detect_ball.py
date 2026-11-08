"""Run Osprey's green-ball detector over the FPV clip and burn its boxes in.

Uses the same detector the system runs (osprey.perception.ballcolor.find_balls, the HSV
green-blob path; the Hailo YOLO half only runs on the Pi). Reads FPV.mov, writes
FPV_det.mov (same frames and timing, boxes drawn) and FPV_det.json (per-frame boxes).

    .venv/bin/python videos/detect_ball.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from osprey.perception import ballcolor  # noqa: E402

SRC, OUT, JSON_OUT = HERE / "FPV.mov", HERE / "FPV_det.mov", HERE / "FPV_det.json"
CONFIRM = 2       # show a box once the ball is seen in 2 of the last 3 frames (drops 1-frame static blips)
HOLD = 3          # keep the last box for up to this many frames through analog static dropouts
BOX = (60, 255, 120)   # BGR lime
FONT = cv2.FONT_HERSHEY_DUPLEX


def draw(img, bbox, conf):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox
    pad = 6
    p1 = (int(x1 * w) - pad, int(y1 * h) - pad)
    p2 = (int(x2 * w) + pad, int(y2 * h) + pad)
    cv2.rectangle(img, p1, p2, BOX, 2, cv2.LINE_AA)
    text = f"GREEN BALL {conf:.2f}"
    (tw, th), base = cv2.getTextSize(text, FONT, 0.45, 1)
    ty = p1[1] - 4 if p1[1] - th - 8 > 0 else p2[1] + th + 6
    cv2.rectangle(img, (p1[0] - 1, ty - th - 4), (p1[0] + tw + 6, ty + base - 1), BOX, -1)
    cv2.putText(img, text, (p1[0] + 3, ty - 1), FONT, 0.45, (0, 0, 0), 1, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(str(SRC))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "8", "-preset", "medium",
         "-pix_fmt", "yuv420p", str(OUT)], stdin=subprocess.PIPE)
    frames, last, miss, n, recent = [], None, 0, 0, []
    while True:
        ok, img = cap.read()
        if not ok:
            break
        t = round(n / fps, 3)
        r = ballcolor.find_balls(img)
        tgt = r["target"]
        recent = (recent + [tgt is not None])[-3:]
        if tgt and (last is not None or sum(recent) >= CONFIRM):
            last, miss = tgt, 0
        elif last is not None and miss < HOLD:
            miss += 1
        else:
            last = None
        frames.append({"t": t, "detected": tgt is not None,
                       "bbox": [round(v, 4) for v in tgt["bbox"]] if tgt else None,
                       "confidence": round(tgt["confidence"], 3) if tgt else None,
                       "n_green": len(r["greens"])})
        shown = last is not None
        frames[-1]["shown"] = shown
        if shown:
            draw(img, last["bbox"], last["confidence"])
        enc.stdin.write(img.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    JSON_OUT.write_text(json.dumps({"source": SRC.name, "fps": fps, "frames": frames}, indent=1))
    hit = sum(f["detected"] for f in frames)
    print(f"{n} frames, ball detected in {hit}; wrote {OUT.name}, {JSON_OUT.name}")


if __name__ == "__main__":
    main()
