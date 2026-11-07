# Hardware setup — for the human, while Claude builds

Claude builds software in phases that don't need new hardware first (see [implementation plan](implementation-plan.md)). Do these tasks in parallel, in order. Each **Checkpoint** means: tell the Claude session the quoted sentence, and it will verify from its side.

## Ground rules while Claude is working

- **Don't reboot the Pi, unplug the Aurora, or pull the Pi/Mac Ethernet** without telling Claude first. Claude may be mid-test.
- Keep the Pi on venue Wi-Fi (its internet) and on the wired switch (the Mac's link).
- Keep the Mac's USB Ethernet adapter plugged **directly** into the Mac.
- Use the Pi's official 27 W USB-C supply (Hailo + camera draw).
- If something gets unplugged by accident, just say so.

## H1. Build the "ship rail" for the deck camera (≈20 min) — needed by Phase 3

The deck camera declares man overboard when a person crosses a rail line. Depth works 0.3–3 m, indoors, away from windows.

1. Mount the Aurora **right side up**, about 1–1.2 m high (table edge, box or tripod), looking out across open floor. Keep its USB cable plugged straight into the Pi.
2. Tape a line on the floor about **1.5 m** in front of the camera: this is the rail. Floor between the camera and the tape is the "deck"; beyond it, out to about 3 m, is "the water".
3. Keep the background away from windows and direct sun. A plain wall 3–4 m away is ideal.
4. Measure and note the camera height and the distance to the tape.

**Checkpoint:** "Aurora mounted right side up, height X m, rail tape at Y m." Claude grabs a frame and calibrates the rail distance with you standing on the tape.

## H2a. FPV drone video into the Pi (BETAFPV Aquila16, analog 5.8 GHz) — Scout A

The drone has no onboard recording or GPS; its camera goes out over analog 5.8 GHz to the VR03 goggles. Get that same signal into the Pi **live**:

1. **Best: a 5.8 GHz receiver with USB (UVC) output** plugged into the Pi, for example an Eachine ROTG02 / Skydroid-style "5.8G OTG/UVC receiver". Set it to the drone's channel (use the goggles' band/channel or its auto-search). It shows up as a USB webcam.
2. **Alternative: goggles AV-out → USB composite capture dongle → Pi.** Only if your goggles actually have a video-out jack (the VR03's AV-out isn't documented; check the jack and the manual).
3. **Backup only: the goggles' DVR** (microSD, .avi, 640×480 @ 30 fps per the Oscar Liang review). Copy the file to the Pi and replay it as a feed labeled RECORDED FLIGHT. It can't drive the live story (no live sighting → no live dispatch), so use it only if live capture fails.

**Checkpoint:** "Drone receiver plugged into the Pi." Claude checks `/api/video_devices`, switches Scout A to `usb`, and tunes the green-ball detector.

## H2b. Green foam ball = person in the water

The scouts look for a **green foam ball** (person-in-water stand-in; COCO "sports ball" + green color detector). Pick a saturated green that doesn't match anything else in the room; keep green tape/clothing out of the water area.

## H2. Phone scout (≈5 min) — optional fallback for either scout

1. Charge the phone. Any modern phone with Chrome or Safari works. It needs internet (cellular or venue Wi-Fi).
2. Wait for Claude to give you a `https://….trycloudflare.com/scout` URL, open it, allow camera access, and pick "Scout B".
3. Optional: tape the phone to a stick or selfie pole so it looks like a drone view from above.

**Checkpoint:** "Phone ready." Claude will send the URL.

## H3. TurboPi rover (≈45–60 min) — needed by Phase 7

Goal: Claude can SSH into the TurboPi over the wired switch, and the Hiwonder demo can move the pan-tilt camera.

1. Charge the battery fully. Power on the rover.
2. Find out which board and OS it runs: look for a Pi 4 or Pi 5 under the shell, check the Hiwonder manual or card, and note the default username and password. Hiwonder images commonly use `pi` / `raspberrypi` and create a Wi-Fi hotspot named `HW-…`. Verify against your manual.
3. Run Hiwonder's own app or demo once to confirm the camera image and pan-tilt servos move. Note the app/demo name.
4. Plug the TurboPi into the **Ugreen switch** with an Ethernet cable. On the TurboPi (via monitor/keyboard, or by SSH over its hotspot), give it a static wired address the same way we did for the Pi:

   ```bash
   nmcli -t -f NAME,DEVICE con show
   ```

   ```bash
   sudo nmcli con mod "Wired connection 1" ipv4.method manual ipv4.addresses 169.254.50.3/16 ipv6.method link-local
   ```

   ```bash
   sudo nmcli con up "Wired connection 1"
   ```

   If it has no NetworkManager (older image), tell Claude the OS version instead.
5. From the Mac, copy your SSH key (you type the TurboPi password once):

   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519_cobeml.pub pi@169.254.50.3
   ```

   Use the real username if it isn't `pi`.
6. Connect the TurboPi to venue Wi-Fi too (it pushes video to the Pi via the internet tunnel during the demo, so it can drive around untethered).

7. Note whether the Hiwonder app can **drive the chassis** (mecanum wheels) as well as move the pan-tilt, and the name of its Python SDK folder (often under `/home/pi/` or `/home/pi/TurboPi/`).

The TurboPi is now **Scout B, the rover that gets dispatched** to the drone's sighting. It starts beside the deck camera, facing the same way. Claude needs to call the chassis and pan-tilt from Python.

**Checkpoint:** "TurboPi at 169.254.50.3, user X, key copied, Hiwonder demo moves pan-tilt and drives." Claude takes it from there.

## H4. Demo layout (≈10 min, any time)

```text
   [wall]
     ~~~~~~~~~~~~ "water" (3+ m) ~~~~~~~~~~~~   ← person walks here after going "overboard"
     TurboPi (Scout A)            Phone holder (Scout B)
   ─────────── rail tape (1.5 m) ───────────
     "deck"
   [Aurora on stand] ── USB ── [Pi 5 + Hailo] ── Ethernet ── switch ── [Mac display]
                                                        ↑ this cable is the outage demo
```

- Put the Mac where judges can see it, and the switch-to-Mac cable where you can visibly unplug it for 5 s.
- One person plays the man overboard, one holds the phone, one runs the display.

## Stretch (only if everything above works)

- **Drone:** ask the organizers which aircraft and flight operator are available, and whether there's an FPV receiver with USB capture. Tell Claude the exact model.
- **Physical MOB button:** plug a Grove button into port **D2** of the Seeeduino base shield. **Checkpoint:** "Grove button on D2."
- **ESP32 radios:** find a USB-C **data** cable (a phone cable usually works). Test it: plug the XIAO into the Mac and run `ls /dev/cu.usbmodem*`; a port should appear. **Checkpoint:** "ESP32 shows on the Mac with the new cable."

## If something breaks

| Symptom | Fix |
|---|---|
| `ssh mob-pi` times out | Check the Mac adapter is directly in the Mac and shows "connected" in System Settings → Network |
| Aurora missing | Replug it directly into the Pi (not the hub), then tell Claude |
| Phone page can't open camera | Must be the `https://` tunnel URL; allow camera access in browser site settings |
| Pi seems slow or rebooting | Check the power supply is the 27 W one; tell Claude to read `vcgencmd get_throttled` |
