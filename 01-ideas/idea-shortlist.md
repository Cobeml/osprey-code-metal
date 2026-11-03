# Five project directions

These are proposed directions, ranked by how quickly they can demonstrate the mission with the listed equipment. No project is selected. Hardware access comes from the [organizer inventory](../02-equipment/source/Hackathon%20Hardware%20Details.pdf); all performance and acceptance tests below are proposed, not measured.

| Priority and idea | What a responder gains | Equipment and integration | Fallback and main risk |
|---|---|---|---|
| **1. Offline incident board** — strongest baseline | One local list of observations, age, source, location label and acknowledgment | Supplied Grove input → Arduino → USB → Pi → local browser. Exact input depends on kit contents | Manual software reporting or clearly simulated readings. Risk: a polished screen without durable delivery/recovery |
| **2. Hazard breadcrumb nodes** — best communications extension | Conditions reported from a placed node without requiring Internet | Suitable environmental sensor; optional ESP32; two compatible LoRa devices for remote link; receiver feeds incident board | USB or local Wi-Fi demonstration. Risk: treating an uncalibrated sensor as a certified hazard detector |
| **3. Human presence review station** — strongest vision direction | Candidate sightings with evidence for human review | Shared compatible camera → Pi/accelerator or CPU → local evidence and compact alert; optional thermal corroboration | Consented recorded footage, labeled replay. Risk: false positives, missed people and camera/runtime mismatch |
| **4. Team location and last contact** — useful if positioning is available | Last reported location and contact age for consenting teammates | GNSS receiver plus paired radio; outdoor test. Indoor UWB is a separate branch requiring tags, anchors and known geometry | Manual markers with explicit provenance. Risk: stale or uncertain coordinates displayed as current and precise |
| **5. Teleoperated inspection scout** — highest integration cost | Human-guided inspection of an inaccessible demo location | Shared robot with working SDK, controller, power and camera; Pi forwards observations | Handheld sensor or stationary pan-tilt camera. Risk: spending the event on locomotion/driver setup |

## What each demo should prove

**Incident board:** generate ten labeled events without Internet; restart the service; recover the same ten once each; acknowledge one; show a disconnected node as stale. A manually entered incident still demonstrates useful information delivery, but must be described as manual.

**Breadcrumb nodes:** trigger a benign environmental change or simulated threshold crossing; interrupt the link; retain the event; reconnect and show its original observation time. Record delivery time separately from responder acknowledgment. LoRa supplies the radio layer; a compatible protocol such as Meshtastic supplies messaging. [Meshtastic hardware requirements](https://meshtastic.org/docs/hardware/devices/)

**Presence review:** use a fixed positive/negative scene set and record misses as well as false alarms. Keep imagery local and transmit a compact alert. Thermal adds surface-temperature evidence; it does not see people through walls. [FLIR explanation](https://www.flir.com/en-gb/discover/home-outdoor/can-thermal-imaging-see-through-walls/)

**Team location:** move between known outdoor points, measure error/latency, then disconnect the node and show the pin becoming stale. GNSS locates the receiver; it does not locate an untagged victim seen by a camera. [GPS accuracy](https://www.gps.gov/gps-accuracy-0)

**Scout:** demonstrate teleoperation, a stop on lost control link, and an observation that reaches the incident board. Defer autonomous mapping or flight unless the team receives a platform with a working example and someone can own it.

## Suggested selection rule

Choose one responder decision, one primary sensor or reporting input, and one delivery path. Prefer a complete outage/recovery demonstration to a larger collection of disconnected sensors. Reserve shared equipment before making it essential. Use the [equipment guide](../02-equipment/equipment-guide.md) and [software list](../04-software/preparation-list.md) to judge each dependency.
