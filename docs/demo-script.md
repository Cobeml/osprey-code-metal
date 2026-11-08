# Demo script (3 minutes)

Roles: **Operator** runs the Mac display. **Overboard** walks over the rail line, then stands out in the water area as the person in the water. **Pilot** flies the FPV drone (Scout A). The TurboPi (Scout B, rover) waits beside the deck camera, facing the same way.

Before judges arrive (5 min):

1. On the Mac: `scripts/deploy.sh --restart`, then open `http://169.254.50.2:8000`, full screen.
2. On the Pi: `ssh mob-pi '~/osprey/scripts/tunnel.sh'`; start the TurboPi client with the printed tunnel URL (see README). Power the drone and its USB receiver on the Pi.
3. Press **D** on the display: ship = Aurora, drone A = USB rx, rover B = TurboPi (or SIM / recorded if a device is down; the tile says so).
4. Check every tile says LIVE and the banner says DECK WATCH. Close the drawer (D).

| Time | Who | Action | What the judges see |
|---|---|---|---|
| 0:00 | Operator | "A ship's deck camera watches the rail." | Navy DECK WATCH status, ship-cam tile with the rail line |
| 0:15 | Overboard | Walk from the deck across the tape and keep going | Status turns red: MAN OVERBOARD; ✕ overboard point; drone and rover launch automatically (rover pill EN ROUTE, along the deck camera's overboard bearing); drift estimate starts growing |
| 0:35 | Operator | "Scouts search. Nobody pressed a button." | ESTIMATE area with model/data labels |
| 0:40 | Pilot | Fly the drone over the water area | Drone tile (LIVE FPV) |
| 0:50 | Pilot | Bring the person in the water into view | Drone feed grows to the top of the column with a candidate box and Confirm / Not a person under it |
| 0:55 | Operator | Click Confirm person | Status green TRACKING; drift area shrinks onto the drone's fix; "fix → rover" on the timeline (fix is sim coords, advisory to the TurboPi) |
| 1:15 | — | Rover camera finds the person | Rover auto-associates (≤ 50 m), APPROACHING, then ON SCENE |
| 1:25 | Operator | Pull the Mac's Ethernet cable for 5 s (backup: D → Software outage 5 s) | LINK LOST ribbon, dimmed screen, last grabs with ticking ages |
| 1:35 | Operator | Plug it back in | Current state and live video back in ≤ 3 s, timeline fills with history chips (dashed) |
| 1:50 | Overboard | Duck out of view (behind a chair) so neither scout sees them | Tiles say CONTACT LOST with the last-sighting grab; after 6 s the banner turns amber and the drift area grows from the last sighting |
| 2:20 | Overboard | Step back into view | Contact resumes automatically (≤ 50 m) — or, for the 80 m case, D → "Reappear 80 m away" shows a candidate that needs CONFIRM |
| 2:40 | Operator | END INCIDENT (click twice) | Blue INCIDENT ENDED; history preserved; deck watch re-armed |

Fallback order if hardware fails mid-demo: switch that node to SIM in the drawer (labeled), keep going.
