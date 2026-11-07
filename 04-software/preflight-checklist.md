# Before arrival and first hour checklist

These are preparation tasks and proposed checks, not completed installations or hardware tests. Select tools from the [priority list](preparation-list.md). Mac preparation and Linux target setup remain separate.

## Before arrival

- [ ] Confirm laptop OS/CPU, team skills and one candidate project. Review the [open-ocean MOB proposal](../01-ideas/open-ocean-mob-plan.md) and confirm a demonstrable fallback.
- [ ] Verify Git, familiar editor, Python and SSH. Download Arduino IDE from its official installer page.
- [ ] Obtain exact board and Grove module IDs; cache the matching board core, libraries and basic examples.
- [ ] Prepare a Python environment and pySerial; choose a small local storage/display path. Add only the selected vision/radio/UI branch.
- [ ] Save installer files, target-specific packages, model weights, firmware, documentation and sample input locally. Record versions and licenses. Cache maps and every browser asset if mapping is chosen.
- [ ] Download an organizer-approved recovery image and Imager; bring suitable card reader only if applicable. Do not overwrite a working borrowed image by default.
- [ ] Bring known data-capable USB cables, required USB adapters, an Ethernet option, and confirmed display/camera/power connectors.
- [ ] Rehearse with clearly labeled synthetic/replay data. Record what works on the laptop separately from what still needs hardware.

## Safe starting checks

On the preparation laptop:

```sh
cd '/Users/dexter/Projects/code-metal-hackathon/04-software/starter'
git rev-parse --show-toplevel
git --version
git status --short
python3 --version
python3 -m json.tool examples/event.example.json
```

When choosing Python, the standard [venv workflow](https://docs.python.org/3/tutorial/venv.html) is:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyserial
python -m pip check
python -m serial.tools.list_ports
```

Commands are unrun instructions. No serial port is expected without hardware. Cache and test packages separately on the laptop and target.

November 3 repository boundary: the whole workspace is on unborn `main`, with no remote or initial commit; the former starter `.git` was promoted to the workspace root and its files preserved. Contributor identity was previously unset; check it when a commit is actually authorized. The following are optional, unrun setup/commit examples, not authorization. Run them at the workspace root and stage only an explicitly reviewed file list. Starter-local ignore rules do not automatically protect other workspace paths:

```sh
cd '/Users/dexter/Projects/code-metal-hackathon'
git rev-parse --show-toplevel
git config --local user.name 'YOUR NAME'
git config --local user.email 'YOUR EMAIL'
# Replace the placeholder with an explicitly reviewed, authorized file list:
git add -- 'path/to/reviewed-file'
git diff --cached --check
git diff --cached
# After reviewing the staged files:
git commit -m 'Initialize hackathon workspace'
```

No remote or public license is selected.

## Organizer questions with the highest setup value

1. What are the exact microcontroller, Grove shield and 40-in-1 kit models? Which board core, libraries, voltage and examples work?
2. What is the accelerator make/model? What Pi OS image, runtime, cooling and compiled models are preinstalled? Is any camera guaranteed?
3. Which shared cameras, thermal sensors, LiDAR, radios, robots and drones are available, in what quantities, with which known-good demos? Can essential items be reserved?
4. For LoRa/UWB, what board variants, antennas, firmware and anchor/tag counts exist? What configurations are permitted at the venue?
5. Does the outage scenario remove Internet, venue Wi-Fi, cellular or all three? May teams run their own local access point? Is a router/Ethernet infrastructure available?
6. What batteries, output modes, chargers, cables and demo areas are supplied? What are the robot/drone operating rules?
7. Are sponsor tools, APIs, repository licenses or existing responder clients required? What are the judging criteria and exact schedule?

These questions are saved here; none has been sent externally.

## First hour on site

| Timebox | Intended outcome |
|---|---|
| 0–15 minutes | Photograph/record actual labels, image versions, interfaces and power ratings; confirm checkout access |
| 15–30 minutes | Boot the supplied Pi; compile/upload the controller's basic example; read one sensor independently |
| 30–45 minutes | Transfer one valid reading over USB and preserve units/source/time |
| 45–60 minutes | Store and display that observation locally; save the working code/version snapshot |

Resolve failures before adding the camera, radio or robot extension.

## Proposed offline acceptance checks

- **Cold start:** start processes and load the page without Internet; verify there are no missing remote assets.
- **Persistence:** generate ten unique simulated events, restart and recover exactly ten.
- **Duplicate delivery:** replay one event and retain one incident, not two.
- **Link outage:** retain an unsent event, reconnect and preserve its original observation time.
- **Freshness:** unplug a source and show stale/unknown status rather than the last reading as current.
- **Human review:** distinguish received, displayed and acknowledged states.
- **Location:** display whose position is represented, its source, age and uncertainty.
- **Optional vision:** record misses and false alarms on a defined scene set; separate replay, CPU and accelerator results.
- **Optional motion:** prove stop behavior on loss of commands before demonstrating mobility.

Record versions, input type and actual outcomes. Imports and replay do not establish hardware or field performance.
