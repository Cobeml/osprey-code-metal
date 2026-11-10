"""Sub-10-second hype edit: project highlights cut on the beat with public-domain
U.S. Navy / USCG footage.

    .venv/bin/python videos/make_hype.py      # -> videos/osprey-hype.mp4

Stock (videos/stock/, gitignored, from Wikimedia Commons, public domain U.S. government work):
  jet_launch.webm   F-A-18F Super Hornets launch from USS Abraham Lincoln (999721)
  small_boats.webm  USS Portland (LPD 27) Artemis I Small Boat Recovery (868323)
  uscg_rescue.webm  USCG Short; Caribbean Rescue
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import music  # noqa: E402

OUT = HERE / "osprey-hype.mp4"
WORK = HERE / "_final_build"
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
W, H, FPS = 1920, 1080, 30
BPM = 150
BEAT = 60 / BPM            # 0.4 s
END_CARD = 1.2

UI, O1, O2 = "demo2_ui.mov", "demo1_outside.MOV", "demo2-outside.MOV"
SIM, DRONE, CELEB = "sim_capture.mp4", "drone-intercut.mp4", "celebration_outside.MOV"
JET, BOATS, USCG = "stock/jet_launch.webm", "stock/small_boats.webm", "stock/uscg_rescue.webm"
UI_MODAL = (1760, 990, 560, 330)
USCG_CROP = (1080, 608, 0, 656)
STOCK_TAG = "U.S. NAVY / USCG FOOTAGE"
SIM_TAG = "CONCEPT SIM"

# (src, start, beats, speed, crop, text, flash, tag)
SHOTS = [
    (UI, 28.6, 2, 1.0, (1600, 900, 0, 0), "MAN OVERBOARD", True, None),
    (JET, 27.95, 1, 1.0, None, None, True, STOCK_TAG),
    (O1, 25.7, 1, 1.0, None, None, False, None),
    (UI, 26.25, 1, 1.0, (960, 540, 1920, 0), None, True, None),
    (USCG, 0.5, 1, 1.0, USCG_CROP, None, False, STOCK_TAG),
    (SIM, 6.0, 1, 2.0, None, None, False, SIM_TAG),
    (UI, 30.0, 1, 4.0, (1080, 608, 0, 500), None, False, None),
    (BOATS, 14.2, 1, 1.5, None, None, True, STOCK_TAG),
    (DRONE, 1.8, 1, 1.0, None, None, False, None),
    (DRONE, 4.2, 1, 1.5, None, None, False, None),
    (USCG, 8.3, 1, 1.0, USCG_CROP, "FIND.", True, STOCK_TAG),
    (DRONE, 11.2, 1, 1.0, None, None, False, None),
    (UI, 53.6, 1, 1.0, UI_MODAL, None, True, None),
    (SIM, 33.5, 1, 2.0, None, None, False, SIM_TAG),
    (USCG, 14.8, 1, 1.0, USCG_CROP, "FOLLOW.", True, STOCK_TAG),
    (O2, 57.3, 1, 1.5, None, None, False, None),
    (UI, 93.0, 1, 1.0, UI_MODAL, None, True, None),
    (SIM, 46.0, 1, 1.0, None, None, False, SIM_TAG),
    (CELEB, 1.4, 2, 1.0, None, "BRING THEM HOME.", True, None),
]


def esc(t):
    return t.replace(":", "\\:").replace("'", "’").replace(",", "\\,")


def main():
    WORK.mkdir(exist_ok=True)
    beats = sum(s[2] for s in SHOTS)
    slams = [b for b, s in zip(__import__("itertools").accumulate([0] + [s[2] for s in SHOTS]), SHOTS) if s[5]]
    total = beats * BEAT + END_CARD
    assert total < 10, total
    mus = WORK / "hype_music.wav"
    music.render_hype(str(mus), beats, BPM, slams=slams)

    inputs, parts, labels = [], [], []
    grade = "eq=contrast=1.22:saturation=1.3:brightness=0.01,vignette=angle=PI/4.5"
    for k, (src, s, nb, sp, crop, txt, flash, tag) in enumerate(SHOTS):
        d = nb * BEAT
        inputs += ["-ss", f"{max(0, s - 1):.3f}", "-i", str(HERE / src)]
        pre = s - max(0, s - 1)
        ch = f"[{k}:v]trim=start={pre:.3f}:end={pre + d * sp + 0.2:.3f},setpts=(PTS-STARTPTS)/{sp},fps={FPS}"
        if crop:
            cw, chh, cx, cy = crop
            ch += f",crop={cw}:{chh}:{cx}:{cy}"
        ch += f",scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1"
        # punch-in + shake
        ch += (f",zoompan=z='1.04+0.010*on':x='iw/2-iw/zoom/2+10*sin(on*2.3)':y='ih/2-ih/zoom/2+7*cos(on*1.9)'"
               f":d=1:s={W}x{H}:fps={FPS},{grade},format=yuv420p")
        if tag:
            ch += (f",drawtext=fontfile='{FONT_B}':text='{esc(tag)}':x=w-text_w-36:y=h-56:fontsize=22"
                   f":fontcolor=white@0.75:box=1:boxcolor=black@0.4:boxborderw=6")
        if txt:
            ch += (f",drawtext=fontfile='{FONT}':text='{esc(txt)}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=150"
                   f":fontcolor=white:borderw=6:bordercolor=black@0.85:shadowx=8:shadowy=8:shadowcolor=black@0.6")
        if flash:
            ch += ",drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:enable='lt(t,0.067)'"
        ch += f",trim=duration={d:.4f},setpts=PTS-STARTPTS[v{k}]"
        parts.append(ch)
        labels.append(f"[v{k}]")
    n = len(SHOTS)
    inputs += ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={END_CARD}"]
    parts.append(
        f"[{n}:v]format=yuv420p,"
        f"drawtext=fontfile='{FONT}':text='OSPREY':x=(w-text_w)/2:y=(h-text_h)/2-40:fontsize=210:fontcolor=white,"
        f"drawtext=fontfile='{FONT_B}':text='{esc('MAN-OVERBOARD RESPONSE  ·  TEAM 29')}':x=(w-text_w)/2:y=h/2+110:fontsize=40:fontcolor=0x6fe0d0,"
        f"drawtext=fontfile='{FONT_B}':text='{esc('Includes public-domain U.S. Navy and USCG footage. Simulation shots are illustrative.')}'"
        f":x=(w-text_w)/2:y=h-60:fontsize=22:fontcolor=white@0.6,"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.9:t=fill:enable='lt(t,0.067)',"
        f"fade=t=out:st={END_CARD - 0.35}:d=0.35[vend]")
    labels.append("[vend]")
    parts.append("".join(labels) + f"concat=n={n + 1}:v=1:a=0[vout]")
    inputs += ["-i", str(mus)]
    parts.append(f"[{n + 1}:a]atrim=0:{total:.3f},afade=t=out:st={total - 0.3:.3f}:d=0.3,loudnorm=I=-14:TP=-1.0[aout]")
    graph = WORK / "hype_graph.txt"
    graph.write_text(";\n".join(parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex_script", str(graph),
                    "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(OUT)], check=True)
    print(f"wrote {OUT.name}: {total:.2f} s, {n} shots, slams on beats {slams}")


if __name__ == "__main__":
    main()
