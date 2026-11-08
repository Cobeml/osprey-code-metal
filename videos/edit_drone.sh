#!/usr/bin/env bash
# Intercut the outside view (flight.mov) with the goggle FPV (FPV.mov) of the
# drone taking off and flying to the tennis ball. Output: drone-intercut.mp4
# (1920x1080, 60 fps interpolated, H.264, no audio). Edit the CUTS list to retime.
#
# How the cut points were picked:
# - Takeoff is a match-on-action cut: flight 3.25 s = FPV 4.25 s, so the wide
#   shot cuts mid-climb at 3.55 and the FPV picks up at 4.55.
# - After takeoff the clips drift apart (ball reached at flight ~13.5 s vs FPV
#   ~9.5 s), so later cuts are matched by event rather than a fixed offset.
# - The FPV is an analog feed with static spikes at ~5.7, 10.9, 12.2, 14.0,
#   15.0, 16.8, 17.4 and 18.5 s; every FPV segment sits in a clean stretch.
# - The outside view has a person blocking the lens at 7.6-9.9 s and
#   11.7-13.0 s; outside-view segments avoid both.
set -euo pipefail
cd "$(dirname "$0")"
# FPV_det.mov = FPV.mov with the green-ball detector boxes burned in (detect_ball.py)
[[ FPV_det.mov -nt FPV.mov ]] || ../.venv/bin/python detect_ball.py

FONT="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
OUT=drone-intercut.mp4

# source start end [speed]  (F = flight.mov outside view, P = FPV.mov goggles)
CUTS=(
  "F 1.6   3.55"  # on the pad -> lifts off; cut mid-climb
  "P 4.55  5.6"   # same instant from the drone, climbing and turning
  "F 5.95  7.5"   # wide: drone turns and flies off past the glass (skips the 3.6-5.9 s hover so it follows the FPV moving forward)
  "P 5.8   8.4"   # FPV: out the door, down the hallway past a person
  "F 10.25 11.6"  # wide: beyond the glass, heading for the far door
  "P 8.6   10.8"  # FPV: turns into the room, the ball comes into view
  "F 13.1  13.75" # wide: drone drops low, ball enters frame
  # FPV descent at 2x: floor line rises and the ball grows as it sinks.
  # Four clean chunks back to back, skipping static at 12.2, 14.0 and 15.0 s.
  "P 11.0  12.1  2"
  "P 12.3  13.85 2"
  "P 14.2  14.9  2"
  "P 15.1  16.7  2"
  "F 13.75 14.42" # wide: drone hovering low by the ball (cut before touchdown at ~14.5)
  # FPV low over the ball (end), split to drop 1-frame static at 19.0, 19.5, 19.9 s
  "P 18.7  18.97"
  "P 19.08 19.48"
  "P 19.6  19.88"
  "P 20.0  20.33"
)

label() {
  echo "drawtext=fontfile='$FONT':text='$1':x=48:y=h-88:fontsize=34:fontcolor=white@0.9:box=1:boxcolor=black@0.5:boxborderw=12"
}
# Per segment: crop to 16:9 at 720p, clean up, interpolate to 60 fps, upscale
# to 1080p, sharpen, grade, label. Interpolating per segment (not after the
# concat) keeps motion interpolation from morphing across cuts.
FIT="scale=1280:720:force_original_aspect_ratio=increase:flags=lanczos,crop=1280:720,setsar=1"
CLEAN_F="hqdn3d=1.5:1.5:4:4"                     # phone footage: light denoise
CLEAN_P="deflicker=size=5,hqdn3d=3:2.5:7:6"      # analog goggle feed: steady brightness, kill grain
INTERP="minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
UP="scale=1920:1080:flags=lanczos,unsharp=5:5:0.5:5:5:0"
GRADE="eq=contrast=1.06:saturation=1.12,vignette=angle=PI/5"
LBL_F=$(label "OUTSIDE VIEW")
LBL_P=$(label "DRONE FPV  ·  OSPREY BALL DETECTOR")

n=${#CUTS[@]}; filter=""; inputs=""; i=0
for c in "${CUTS[@]}"; do
  read -r src s e sp <<<"$c"; sp=${sp:-1}
  if [[ $src == F ]]; then idx=0; lbl=$LBL_F; clean=$CLEAN_F; else idx=1; lbl=$LBL_P; clean=$CLEAN_P; fi
  # 2x segments already have 60 real frames per second; 1x ones get interpolated.
  if [[ $sp == 2 ]]; then motion="fps=60"; else motion="fps=30,$INTERP"; fi
  fx=""
  (( i == 0 )) && fx+=",fade=t=in:st=0:d=0.5"
  filter+="[$idx:v]trim=start=$s:end=$e,setpts=(PTS-STARTPTS)/$sp,$FIT,$clean,$motion,$UP,$GRADE,$lbl$fx,format=yuv420p[v$i];"
  inputs+="[v$i]"; i=$((i+1))
  total=$(awk "BEGIN{print ${total:-0} + ($e - $s)/$sp}")
done
filter+="${inputs}concat=n=$n:v=1:a=0,fade=t=out:st=$(awk "BEGIN{print $total - 0.8}"):d=0.8[out]"

# 1080p60 H.264 High, CRF 14 (visually lossless; lands above YouTube's 12 Mbps
# recommendation for 1080p60), 2 s GOP for clean seeking/upload.
ffmpeg -v error -stats -y -i flight.mov -i FPV_det.mov -filter_complex "$filter" -map "[out]" \
  -c:v libx264 -preset slow -crf 14 -tune film -profile:v high -level 4.2 -g 120 \
  -pix_fmt yuv420p -r 60 -movflags +faststart "$OUT"
echo "wrote $OUT ($(ffprobe -v error -show_entries format=duration:format=bit_rate -of csv=p=0 "$OUT"))"
