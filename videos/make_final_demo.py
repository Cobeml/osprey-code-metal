"""Build the final Osprey demo video: concept simulation, then the live hardware demo,
with a synthesized voice-over and an original background score.

    .venv/bin/python videos/make_final_demo.py   # -> osprey-final-demo.mp4 (+ -web.mp4)

Opens cold with osprey-hype.mp4 minus its end card (run make_hype.py first).

Inputs (all in videos/):
  sim_capture.mp4        3D mission simulation, recorded headless by capture_sim.mjs
  demo2-outside.MOV      outside camera, live run (main take)
  demo2_ui.mov           coordinator screen recording of the same run (UI = outside + 13.4 s)
  demo1_outside.MOV      outside camera, earlier take (water sensor dipped in the cup)
  drone-intercut.mp4     drone test flight: outside / FPV with the ball detector overlay
  celebration_outside.MOV
  ../docs/media/osprey-operational-concept.png
Voice-over: Kokoro-82M via tts.py (local). Music: music.py (synthesized, no samples).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import music  # noqa: E402
import tts  # noqa: E402

WORK = HERE / "_final_build"
OUT = HERE / "osprey-final-demo.mp4"
WEB = HERE / "osprey-final-demo-web.mp4"
COLD_OPEN = HERE / "osprey-hype.mp4"   # make_hype.py; 9.6 s cold open ahead of the main cut
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
VOICE, SPEED = "am_michael", 1.12   # Kokoro voice (tts.py)
W, H, FPS = 1920, 1080, 30
UI_OFFSET = 13.4  # demo2: ui_time = outside_time + 13.4 s (audio cross-correlation)

SIM = "sim_capture.mp4"
O2, UI, O1 = "demo2-outside.MOV", "demo2_ui.mov", "demo1_outside.MOV"
DRONE, CELEB = "drone-intercut.mp4", "celebration_outside.MOV"
CONCEPT = "../docs/media/osprey-operational-concept.png"

L_SIM = "CONCEPT SIMULATION  ·  ILLUSTRATIVE VEHICLES, COMPRESSED TIME"
L_OUT = "LIVE DEMO  ·  OUTSIDE VIEW"
L_UI = "LIVE DEMO  ·  OSPREY COORDINATOR"

# Segments in order. src times are in that file's own timeline.
# keys: src, s, e, speed, label, crop (w,h,x,y on the source), tag (top-right), kind
SEGS = [
    dict(id="sim_intro", src=SIM, s=0.0, e=14.0, label=L_SIM, title=True),
    dict(id="sim_search", src=SIM, s=14.0, e=33.0, speed=2.5, label=L_SIM),
    dict(id="sim_lock", src=SIM, s=33.0, e=40.0, label=L_SIM),
    dict(id="sim_close", src=SIM, s=40.0, e=52.0, speed=2.0, label=L_SIM),
    dict(id="build", kind="still", src=CONCEPT, dur=11.5, caption="THE HACKATHON BUILD",
         sub="Green ball = person in the water  ·  cup of water = the sea  ·  TurboPi = rescue boat"),
    dict(id="ball_up", src=O2, s=0.0, e=3.2, label=L_OUT),
    dict(id="armed", src=UI, s=16.4, e=20.0, label=L_UI),
    dict(id="ball_over", src=O2, s=8.0, e=10.4, label=L_OUT),
    dict(id="ball_lost", src=UI, s=23.6, e=25.2, label=L_UI),
    dict(id="dip", src=O1, s=24.8, e=27.6, label="LIVE DEMO  ·  WATER SENSOR INTO THE CUP"),
    dict(id="wet", src=UI, s=25.4, e=27.4, label=L_UI, crop=(960, 540, 1920, 0)),
    dict(id="banner", src=UI, s=27.4, e=29.6, label=L_UI, crop=(1600, 900, 0, 0)),
    dict(id="map", src=UI, s=29.6, e=41.6, speed=2.0, label=L_UI + "  ·  2x", crop=(1080, 608, 0, 500)),
    dict(id="drone", src=DRONE, s=0.6, e=13.0, tag="DRONE TEST FLIGHT"),
    dict(id="candidate", src=UI, s=51.8, e=55.2, label=L_UI),
    dict(id="confirm", src=UI, s=67.4, e=70.6, label=L_UI),
    dict(id="rover_out", src=O2, s=55.0, e=61.0, label=L_OUT),
    dict(id="rover_cam", src=UI, s=88.6, e=94.0, label=L_UI),
    dict(id="rover_close", src=O2, s=77.0, e=83.0, label=L_OUT),
    dict(id="celebrate", src=CELEB, s=0.0, e=5.0, label=L_OUT, audio=0.8),
    dict(id="outro", kind="card", dur=6.0),
]

# voice-over: (segment id, offset into it, text)
VO = [
    ("sim_intro", 0.8, "When someone goes overboard, every minute counts. The first problem is simply finding them."),
    ("sim_intro", 7.0, "Osprey turns a man overboard alarm into a coordinated search. It predicts where wind and current will carry the person, and launches drones and a rescue boat to cover that area."),
    ("sim_lock", 0.3, "When a drone spots them, the swarm locks on and keeps them in sight, while the rescue boat is guided straight in."),
    ("build", 0.3, "For the hackathon, we built it for real. A green ball plays the person, and a cup of water plays the sea. The sensor loadout is modular, configured for each vessel and mission."),
    ("ball_up", 0.2, "A deck camera watches the rail. Once it sees the person on deck, auto man overboard is armed."),
    ("ball_lost", 0.0, "The ball goes over. The water sensor, standing in for a crew wearable, gets wet."),
    ("wet", 1.2, "Osprey raises man overboard instantly. Nobody has to press a button."),
    ("map", 2.0, "The drift model starts growing the search area on the map."),
    ("drone", 0.6, "A drone launches, and Osprey's detector picks out the green ball in its camera feed."),
    ("candidate", 0.2, "Red decoys are rejected. The operator confirms the sighting with one click."),
    ("rover_out", 0.3, "The rover is dispatched to the drone's fix, and closes in with its own camera."),
    ("celebrate", 0.2, "Target reached."),
    ("outro", 0.6, "Osprey. Find them. Follow them. Bring them home."),
]


def run(cmd):
    subprocess.run(cmd, check=True)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode())


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace(",", "\\,")


def text(t, size, y, font=FONT, color="white", extra=""):
    return (f"drawtext=fontfile='{font}':text='{esc(t)}':fontsize={size}:fontcolor={color}"
            f":x=(w-text_w)/2:y={y}{extra}")


def label(t):
    return (f"drawtext=fontfile='{FONT}':text='{esc(t)}':x=48:y=h-84:fontsize=28"
            f":fontcolor=white@0.92:box=1:boxcolor=black@0.55:boxborderw=11")


def tag(t):
    return (f"drawtext=fontfile='{FONT}':text='{esc(t)}':x=w-text_w-48:y=40:fontsize=28"
            f":fontcolor=black:box=1:boxcolor=0xffc23d@0.95:boxborderw=11")


def main():
    WORK.mkdir(exist_ok=True)
    # --- timeline
    t = 0.0
    for sg in SEGS:
        d = sg.get("dur") or (sg["e"] - sg["s"]) / sg.get("speed", 1.0)
        sg["t0"], sg["d"] = t, d
        t += d
    total = t
    at = {sg["id"]: sg for sg in SEGS}

    # --- voice-over
    vo = []
    for i, (sid, off, line) in enumerate(VO):
        wav = WORK / f"vo{i:02d}.wav"
        key = WORK / f"vo{i:02d}.txt"
        stamp = f"{VOICE}|{SPEED}|{line}"
        if not wav.exists() or not key.exists() or key.read_text() != stamp:
            raw = WORK / f"vo{i:02d}_raw.wav"
            tts.synth(line, str(raw), VOICE, SPEED)
            run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ar", "48000", "-ac", "1", str(wav)])
            key.write_text(stamp)
        start = at[sid]["t0"] + off
        vo.append((start, dur(wav), wav, line))
    for (a, da, _, la), (b, _, _, lb) in zip(vo, vo[1:]):
        if a + da > b - 0.15:
            print(f"WARNING VO overlap: '{la[:30]}' ends {a+da:.1f} > next starts {b:.1f}")

    # --- music
    cues = dict(search=at["sim_intro"]["t0"] + 6.0, lock=at["sim_lock"]["t0"],
                build_card=at["build"]["t0"], demo=at["ball_up"]["t0"],
                alarm=at["wet"]["t0"] + 1.0, drone=at["drone"]["t0"], celebrate=at["celebrate"]["t0"])
    mus = WORK / "music.wav"
    music.render(str(mus), total, cues)

    # --- video graph
    inputs, fparts, vlabels = [], [], []

    def inp(path, *pre):
        inputs.extend([*pre, "-i", str(path)])
        return len([x for x in inputs if x == "-i"]) - 1

    norm = f"fps={FPS},format=yuv420p,setsar=1"
    for k, sg in enumerate(SEGS):
        kind = sg.get("kind", "clip")
        if kind == "clip":
            i = inp(HERE / sg["src"])
            s, e, sp = sg["s"], sg["e"], sg.get("speed", 1.0)
            ch = f"[{i}:v]trim=start={s}:end={e},setpts=(PTS-STARTPTS)/{sp}"
            if "crop" in sg:
                cw, chh, cx, cy = sg["crop"]
                ch += f",crop={cw}:{chh}:{cx}:{cy},scale={W}:{H}:flags=lanczos"
            elif sg["src"] == UI:
                ch += f",scale=-2:{H}:flags=lanczos,pad={W}:{H}:(ow-iw)/2:0:color=0x1b2433"
            else:
                ch += f",scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
            ch += f",{norm}"
            if sg.get("label"):
                ch += "," + label(sg["label"])
            if sg.get("tag"):
                ch += "," + tag(sg["tag"])
            if sg.get("title"):
                ch += (",drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill:enable='lt(t,4.6)'"
                       + "," + text("OSPREY", 150, "(h/2)-150", extra=":enable='lt(t,4.6)':alpha='if(lt(t,0.6),t/0.6,if(lt(t,4.0),1,(4.6-t)/0.6))'")
                       + "," + text("Man-overboard response under degraded comms", 44, "(h/2)+30", FONT_REG,
                                    extra=":enable='lt(t,4.6)':alpha='if(lt(t,0.9),0,if(lt(t,1.5),(t-0.9)/0.6,if(lt(t,4.0),1,(4.6-t)/0.6)))'")
                       + ",fade=t=in:st=0:d=0.8")
        elif kind == "still":
            i = inp(HERE / sg["src"], "-loop", "1", "-t", f"{sg['d']:.3f}", "-framerate", str(FPS))
            ch = (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                  f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=white,{norm},"
                  f"drawbox=x=0:y=ih-200:w=iw:h=200:color=black@0.7:t=fill,"
                  + text(sg["caption"], 54, "h-180", color="0xffc23d") + ","
                  + text(sg["sub"], 32, "h-104", FONT_REG)
                  + ",fade=t=in:st=0:d=0.5")
        else:  # outro card
            i = inp(f"color=c=0x0b1220:s={W}x{H}:r={FPS}:d={sg['d']:.3f}", "-f", "lavfi")
            ch = (f"[{i}:v]{norm},"
                  + text("OSPREY", 150, "(h/2)-190", extra=":alpha='min(1,t/0.8)'") + ","
                  + text("Find. Follow. Bring them home.", 56, "(h/2)", color="0x6fe0d0", extra=":alpha='min(1,max(0,(t-0.6)/0.8))'") + ","
                  + text("Team 29  ·  CodeMetal Forge 2026", 34, "(h/2)+110", FONT_REG, color="white@0.8",
                         extra=":alpha='min(1,max(0,(t-1.2)/0.8))'") + ","
                  + text("Opening includes public-domain U.S. Navy and USCG footage", 24, "h-70", FONT_REG,
                         color="white@0.55", extra=":alpha='min(1,max(0,(t-1.2)/0.8))'")
                  + f",fade=t=out:st={sg['d']-1.2:.3f}:d=1.2")
        # trim to the exact planned length so audio cues stay in sync
        ch += f",trim=duration={sg['d']:.4f},setpts=PTS-STARTPTS[v{k}]"
        fparts.append(ch)
        vlabels.append(f"[v{k}]")
    fparts.append("".join(vlabels) + f"concat=n={len(SEGS)}:v=1:a=0[vmain]")

    # --- audio graph: music (ducked under VO), VO, celebration audio
    mi = inp(mus)
    vo_labels = []
    for j, (start, _, wav, _) in enumerate(vo):
        vi = inp(wav)
        ms = int(start * 1000)
        fparts.append(f"[{vi}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,"
                      f"volume=1.6,adelay={ms}|{ms}[vo{j}]")
        vo_labels.append(f"[vo{j}]")
    fparts.append("".join(vo_labels) + f"amix=inputs={len(vo_labels)}:normalize=0,apad,atrim=0:{total:.3f},asplit=2[vomix][vokey]")
    fparts.append(f"[{mi}:a]volume=0.42,atrim=0:{total:.3f}[mus]")
    fparts.append("[mus][vokey]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500:makeup=1[musduck]")
    cel = at["celebrate"]
    ci = inp(HERE / CELEB)
    cms = int(cel["t0"] * 1000)
    fparts.append(f"[{ci}:a:0]atrim=0:{cel['d']:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                  f"volume={cel['audio']},afade=t=in:d=0.2,afade=t=out:st={cel['d']-0.6:.3f}:d=0.6,adelay={cms}|{cms}[cel]")
    fparts.append(f"[vomix][musduck][cel]amix=inputs=3:normalize=0,atrim=0:{total:.3f},"
                  f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[amain]")
    # cold open: the hype edit without its end card, so its final slam lands on the OSPREY title;
    # its audio runs full length and the end hit rings out under the start of the main cut
    import make_hype
    cold = sum(sh[2] for sh in make_hype.SHOTS) * make_hype.BEAT
    hi = inp(COLD_OPEN)
    cms0 = int(cold * 1000)
    fparts.append(f"[{hi}:v]trim=duration={cold:.4f},setpts=PTS-STARTPTS,{norm}[hv]")
    fparts.append(f"[{hi}:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,volume=-2dB,apad[ha]")
    fparts.append(f"[amain]adelay={cms0}|{cms0}[amd]")
    fparts.append(f"[hv][vmain]concat=n=2:v=1:a=0[vout]")
    fparts.append(f"[ha][amd]amix=inputs=2:normalize=0:duration=shortest,atrim=0:{cold + total:.3f}[aout]")

    graph = WORK / "graph.txt"
    graph.write_text(";\n".join(fparts))
    run(["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex_script", str(graph),
         "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(OUT)])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT), "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-pix_fmt", "yuv420p", "-g", str(FPS * 2), "-c:a", "copy", "-movflags", "+faststart", str(WEB)])
    print(f"\nwrote {OUT.name} + {WEB.name}: {cold + total:.1f} s ({cold:.1f} s cold open)")
    for sg in SEGS:
        print(f"  {cold + sg['t0']:6.1f}  {sg['id']}")


if __name__ == "__main__":
    main()
