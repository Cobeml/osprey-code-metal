#!/usr/bin/env bash
# Product demo: cut between the outside camera (demo2-outside.MOV) and the
# Osprey UI screen recording (demo2_ui.mov), keeping the outside audio running
# unbroken, then the celebration clip. Output: osprey-demo.mp4 (1080p60).
#
# Sync: audio cross-correlation of the two recordings puts UI time =
# outside time + 13.4 s (file creation times agree to ~2 s).
# Only the picture switches; the audio is the outside track from 0 to the end,
# so no speech is cut.
set -euo pipefail
cd "$(dirname "$0")"

OUTSIDE=demo2-outside.MOV
UI=demo2_ui.mov
OFFSET=13.4        # ui_time = outside_time + OFFSET
OUT=osprey-demo.mp4
FONT="/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# picture source per span of the outside timeline (O = outside, U = UI). Spans
# must tile 0..END with no gaps.
END=83.0
CUTS=(
  "O 0    3"    # crew member holds up the green ball (person in the water stand-in)
  "U 3    8"    # deck cam: green ball in view, auto-MOB ARMED
  "O 8    10"   # ball goes over
  "U 10   17"   # deck cam: ball LOST -> MOB opens, drift search area on the map
  "O 17   27"   # team at the laptop, water sensor wet
  "U 27   31"   # search area growing, drone launching
  "O 31   37"   # pilot flies the drone
  "U 37   45"   # drone feed: green ball candidate 95%, red decoys rejected
  "O 45   49"   # pilot's phone view
  "U 49   55"   # drone tracking the green ball, sighting confirmed
  "O 55   64"   # rover drives out
  "U 64   70"   # rover camera heading to the sighting
  "O 70   75"   # rover closing in
  "U 75   83"   # rover camera: green ball candidate 94%, decoys ignored
)

label() {
  echo "drawtext=fontfile='$FONT':text='$1':x=48:y=h-88:fontsize=32:fontcolor=white@0.92:box=1:boxcolor=black@0.5:boxborderw=12"
}
O_FIT="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=60"
# UI is 16:10: fit the whole screen, pad the sides
U_FIT="scale=-2:1080:flags=lanczos,pad=1920:1080:(ow-iw)/2:0:color=0x1b2433,setsar=1,fps=60"
LBL_O=$(label "OUTSIDE VIEW")
LBL_U=$(label "OSPREY COORDINATOR  ·  LIVE SCREEN RECORDING")

filter=""; inputs=""; i=0
for c in "${CUTS[@]}"; do
  read -r src s e <<<"$c"
  if [[ $src == O ]]; then
    filter+="[0:v]trim=start=$s:end=$e,setpts=PTS-STARTPTS,$O_FIT,$LBL_O,format=yuv420p[v$i];"
  else
    us=$(awk "BEGIN{print $s + $OFFSET}"); ue=$(awk "BEGIN{print $e + $OFFSET}")
    filter+="[1:v]trim=start=$us:end=$ue,setpts=PTS-STARTPTS,$U_FIT,$LBL_U,format=yuv420p[v$i];"
  fi
  inputs+="[v$i]"; i=$((i+1))
done
n=$i
# main section: video segments + unbroken outside audio
filter+="${inputs}concat=n=$n:v=1:a=0,fade=t=in:st=0:d=0.6[mv];"
filter+="[0:a:0]atrim=0:$END,asetpts=PTS-STARTPTS,afade=t=in:d=0.4,aformat=sample_rates=48000:channel_layouts=stereo[ma];"
# celebration clip with its own audio, short crossfade-free join, fade out
filter+="[2:v]setpts=PTS-STARTPTS,$O_FIT,$LBL_O,format=yuv420p,fade=t=out:st=4.2:d=0.8[cv];"
filter+="[2:a:0]asetpts=PTS-STARTPTS,afade=t=out:st=4.2:d=0.8,aformat=sample_rates=48000:channel_layouts=stereo[ca];"
filter+="[mv][ma][cv][ca]concat=n=2:v=1:a=1[outv][outa]"

ffmpeg -v error -stats -y -i "$OUTSIDE" -i "$UI" -i celebration_outside.MOV \
  -filter_complex "$filter" -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 18 -profile:v high -pix_fmt yuv420p -r 60 -g 120 \
  -c:a aac -b:a 192k -movflags +faststart "$OUT"
echo "wrote $OUT ($(ffprobe -v error -show_entries format=duration,bit_rate -of csv=p=0 "$OUT"))"
