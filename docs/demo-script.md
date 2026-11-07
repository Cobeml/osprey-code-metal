# Demo script (3 minutes)

Roles: **Operator** runs the Mac display. **Overboard** walks over the rail line. **Scout B** holds the phone. Scout A (TurboPi) sits on the floor facing "the water".

Before judges arrive (5 min):

1. On the Mac: `scripts/deploy.sh --restart`, then open `http://169.254.50.2:8000`, full screen.
2. On the Pi: `ssh mob-pi '~/osprey/scripts/tunnel.sh'` → open the printed `…/scout` URL on the phone, pick Scout B. Start the TurboPi client (see README).
3. Press **D** on the display and check the source buttons: ship = Aurora, A and B = real (or SIM if a device is down; the tile then says [SIM]).
4. Check every tile says LIVE and the banner says DECK WATCH. Close the drawer (D).

| Time | Who | Action | What the judges see |
|---|---|---|---|
| 0:00 | Operator | "A ship's deck camera watches the rail." | Grey DECK WATCH banner, ship-cam tile with the rail line |
| 0:15 | Overboard | Walk from the deck across the tape and keep going | Banner turns red: MAN OVERBOARD; ✕ overboard point; deck-cam grab retained; drift estimate starts growing |
| 0:35 | Operator | "Scouts search. Nobody pressed a button." | ESTIMATE area with model/data labels |
| 0:45 | Scout B | Point the phone at the person | Candidate box on Scout B, CONFIRM button appears |
| 0:55 | Operator | Click CONFIRM PERSON | Banner green TRACKING; sighting marker with age |
| 1:05 | — | Scout A sees the person | Scout A auto-associates (≤ 50 m), rover camera starts following |
| 1:25 | Operator | Pull the Mac's Ethernet cable for 5 s (backup: D → Software outage 5 s) | LINK LOST ribbon, dimmed screen, last grabs with ticking ages |
| 1:35 | Operator | Plug it back in | Current state and live video back in ≤ 3 s, timeline fills with history chips (dashed) |
| 1:50 | Overboard | Hide from both cameras (crouch behind a chair) | Tiles say CONTACT LOST with the last-sighting grab; after 6 s the banner turns amber and the drift area grows from the last sighting |
| 2:20 | Overboard | Reappear in view | Contact resumes automatically (≤ 50 m) — or, for the 80 m case, D → "Reappear 80 m away" shows a candidate that needs CONFIRM |
| 2:40 | Operator | END INCIDENT (click twice) | Blue INCIDENT ENDED; history preserved; deck watch re-armed |

Fallback order if hardware fails mid-demo: switch that node to SIM in the drawer (labeled), keep going.
