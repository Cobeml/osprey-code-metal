# Research — open-ocean man-overboard response

Collected November 7, 2026. This is a focused synthesis of sources reviewed during planning. Vendor descriptions, research prototypes and operational reports carry different evidence.

## Existing capabilities

| System | Relevant evidence |
| --- | --- |
| Irish Coast Guard thermal drones | Agency describes operational thermal-equipped drones supporting searches. Autonomous tracking and radio-outage behavior need separate evidence. [Agency equipment](https://coastguard.gov.ie/about-us/our-technology-and-equipment/) |
| Royal Navy Minerva trials | Controlled trial located a dummy, deployed a test package and hovered to mark the location. [Navy report](https://www.royalnavy.mod.uk/news/2021/july/02/210702-drone-trials-mob) |
| SALVOR ASSIST | Vendor describes ship-launched search, thermal AI and flotation delivery. Independent end-to-end performance was not verified. [Mission modules](https://salvor-maritime.com/missions) |
| US Coast Guard SAROPS | Monte Carlo search planning and allocation of resources provide a reference for uncertainty and detection probability. [SAROPS](https://www.dcms.uscg.mil/Our-Organization/Assistant-Commandant-for-Acquisitions-CG-9/International-Acquisition/sarops/) |

## Physical and algorithmic constraints

A thermal target's visibility depends on exposed area, contrast, altitude, optics and environmental conditions. A marine pilot study examined low contrast and operating altitude. This supports measuring performance under the actual camera and sea conditions rather than assuming detection from nominal resolution. [Thermal pilot study](https://www.mdpi.com/2504-446X/8/3/76)

Geolocating an image detection requires intrinsic calibration, camera orientation and position, a surface assumption and aligned time. The drone's location alone is insufficient. A local sea-plane projection can be a prototype approximation while uncertainty represents pose and surface error. [Camera geometry](https://docs.opencv.org/4.7.0/d9/d0c/group__calib3d.html)

Leeway modeling uses current and object-specific wind response. A person's actual drift depends on conditions and configuration. Unknown currents should be represented as uncertainty or explicit scenario assumptions. [OpenDrift Leeway](https://opendrift.github.io/autoapi/opendrift/models/leeway/index.html)

## Proposed contribution

The candidate contribution is reliable sharing of target evidence during intermittent communications. Keep source observations, prediction, visual-contact status and communications freshness separate. Demonstrate clean recovery without allowing delayed packets to make stale evidence look current.

Novelty is an open hypothesis. Existing products and research already provide pieces of detection, tracking, drift forecasting and mission management. Validate the workflow with maritime operators and compare actual competitor capabilities before claiming uniqueness.

## Code and data availability

[MAMMS](https://zenodo.org/records/17979190) includes thermal UAV sequences and ground-truth/telemetry for a geolocation subset, but requires an access agreement. [SeaDronesSee](https://github.com/Ben93kie/SeaDronesSee) supplies RGB maritime benchmarks. Dataset access, licenses, modality and available telemetry need checking before selecting a replay.

The [PDMS paper repository](https://github.com/DTU-IPL/pdms-man-overboard) presently contains a README promising code after acceptance. Treat the paper as research context rather than an available implementation dependency.

## Evaluation implication

Compare identical observations and outage schedules against a simple last-seen-position baseline. Measure location error, freshness, region area, empirical coverage, bandwidth and recovery time. Include wrong assumptions and distractors. The team has no measured open-ocean results yet.
