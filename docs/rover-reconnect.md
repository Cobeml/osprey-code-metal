# Rover back onto Wi-Fi + tunnel after charging

The rover reaches the ground over the venue Wi-Fi through a Cloudflare **quick tunnel**. The tunnel's
`https://<random>.trycloudflare.com` address is new every time cloudflared starts, and the rover only
knows the address written into `~/osprey-rover/rover.env`. After the ground Pi or its tunnel has been
down (charging, reboot), run these steps **with the rover on the cable**. All commands run on the Mac
from the repo, unless marked otherwise.

Nothing here starts by itself at boot: not the ground server, not the tunnel, not the rover client
(`autostart` is off). On the rover, Hiwonder's `wifi.service` also deletes the venue Wi-Fi at boot.

## 0. Cables
- Mac: USB Ethernet adapter plugged **straight into the Mac** (it only shows up as `en10` that way).
- Rover: Ethernet into the switch, then power on. **Wait ~1 min**: its IPv4 address `169.254.50.3`
  only appears once it has finished booting.
- macOS sometimes sends 169.254.x.x out over Wi-Fi. If an ssh times out, add `-o BindInterface=en10`.

## 1. Ground Pi: server + tunnel
```bash
ssh mob-pi '~/osprey/scripts/run_pi.sh start'        # ground server on :8000 (if not running)
ssh mob-pi '~/osprey/scripts/tunnel.sh start'        # prints https://<new>.trycloudflare.com/scout
```
Check it from the Mac (should print `{"ok":true,...} 200`):
```bash
curl -s -w ' %{http_code}\n' "$(ssh mob-pi '~/osprey/scripts/tunnel.sh url' | sed 's#/scout$##')/health"
```

View-only dashboard for a computer or phone that isn't on the Ethernet (new link each new tunnel;
the key itself stays the same):
```bash
ssh mob-pi '~/osprey/scripts/tunnel.sh view'       # https://<new>.trycloudflare.com/?k=<key>
```

## 2. Rover: rejoin the venue Wi-Fi (the human types the password)
Hiwonder's `wifi.service` brings its own hotspot back at every boot, so this is needed after each rover
reboot. The name must be exactly `BASE-X Guest`, case included. Right after boot the rover (running its
hotspot) hasn't scanned yet, and the join fails with "No network with SSID found": scan first.
```bash
ssh pi@169.254.50.3 'sudo nmcli dev wifi rescan ifname wlan0; sleep 5; nmcli -t -f SSID dev wifi list ifname wlan0 | grep -c "^BASE-X Guest$"'
```
Then join:
```bash
ssh -t -o BindInterface=en10 pi@169.254.50.3 "sudo nmcli --ask device wifi connect 'BASE-X Guest' ifname wlan0"
```
Check (should show `connected:BASE-X Guest`, then `internet ok`):
```bash
ssh pi@169.254.50.3 'nmcli -t -f DEVICE,STATE,CONNECTION device | grep ^wlan0; ping -c1 -W3 1.1.1.1 >/dev/null && echo internet ok'
```

## 3. Rover: save the new tunnel address
```bash
scripts/deploy_rover.sh urls --trace
```
This asks the ground Pi for the current tunnel address and writes `rover.env`:
`ROVER_URLS=ws://169.254.50.2:8000,https://<new>.trycloudflare.com`. Make sure the second address
matches what step 1 printed. If it says "wired only", the tunnel isn't up: redo step 1.

## 4. Start the rover client
```bash
scripts/deploy_rover.sh                     # copy the latest client (only after code changes)
scripts/deploy_rover.sh stop
scripts/deploy_rover.sh start               # motors ON, URLs from rover.env
```
Motors off (bench test): `scripts/deploy_rover.sh start "$(ssh pi@169.254.50.3 "sed -n 's/^ROVER_URLS=//p' ~/osprey-rover/rover.env")" --hw none`

## 5. Check, then pull the cable
- Dashboard `http://169.254.50.2:8000/`: the Rover B tile shows **LIVE** video, not "RETAINED GRAB".
- `scripts/deploy_rover.sh status` shows `running` and the env line.
- Pull the rover's Ethernet. It should switch to the tunnel in ~6 s: the ground stops hearing it,
  the rover drops the dead link after 4 s, then connects to `wss://<new>.trycloudflare.com`.
  Tested Nov 8: tunnel 6.5 fps, 60-90 ms latency.
- After the cable is out, the Mac can't ssh to the rover (the venue Wi-Fi blocks devices from talking
  to each other). Plug it back in for any change.

## If the tunnel address changes while the rover is on Wi-Fi
The rover can't find the new tunnel by itself. It keeps trying the wired address and the old tunnel,
and meanwhile keeps searching on its own camera, stopping after 60 s. Plug the cable in, then redo
steps 3-5. Only one tunnel should be running: `ssh mob-pi 'pgrep -af "cloudflared tunnel"'`.
