# Man-overboard systems and implementation research

Research collected November 7, 2026. This report consolidates the maritime research used in the [open-ocean project proposal](../../01-ideas/open-ocean-mob-plan.md). Published capabilities and repository contents were reviewed. Local installation, hardware compatibility, and open-ocean performance remain to be tested.

## Existing systems

| System | Evidence and relevance |
| --- | --- |
| Irish Coast Guard drones | The agency describes thermal-equipped drones supporting searches. This establishes operational use of thermal drones, while autonomous acquisition and handoff require separate evidence. [Agency equipment](https://coastguard.gov.ie/about-us/our-technology-and-equipment/) |
| Royal Navy Minerva trials | A controlled trial located a dummy, dropped a test package and hovered to mark the casualty. The report supports the rescue workflow but does not establish autonomous thermal detection. [Trial](https://www.royalnavy.mod.uk/news/2021/july/02/210702-drone-trials-mob) |
| SALVOR ASSIST | Vendor describes a ship-launched drone searching along a corridor, thermal AI detection and flotation delivery. Independent performance was not verified in this review. [Mission modules](https://salvor-maritime.com/missions) |
| US Coast Guard SAROPS | Monte Carlo search planning and resource allocation provide a reference for reasoning about location uncertainty and detection probability. [SAROPS](https://www.dcms.uscg.mil/Our-Organization/Assistant-Commandant-for-Acquisitions-CG-9/International-Acquisition/sarops/) |

## Technical findings

Thermal target visibility varies with contrast, exposed body area, altitude, optics and environmental conditions. A marine pilot study investigates low contrast and operating altitude. Performance must be measured with the selected camera and scenario. [Thermal pilot study](https://www.mdpi.com/2504-446X/8/3/76)

A camera detection supplies a pixel location and a viewing ray. A position on the sea requires camera calibration, aircraft and gimbal orientation, camera position, altitude relative to the water, and aligned timestamps. Sea-plane intersection can support a limited prototype, with pose and wave uncertainty represented explicitly. [Camera geometry](https://docs.opencv.org/4.7.0/d9/d0c/group__calib3d.html)

OpenDrift's Leeway model combines currents and object-specific wind response. Its simulation can inform a search region after observation loss. Drift accuracy depends on forcing data and object assumptions. A fixed confidence percentage requires empirical calibration. [Leeway model](https://opendrift.github.io/autoapi/opendrift/models/leeway/index.html)

## Public code and data

| Resource | Role and limits |
| --- | --- |
| [Hailo Pi examples](https://github.com/hailo-ai/hailo-rpi5-examples) | Candidate device-side detection pipeline when the supplied accelerator and image are compatible. Swimmer detection remains untested. |
| [Roboflow Trackers](https://github.com/roboflow/trackers) and [Supervision](https://github.com/roboflow/supervision) | Association and visual annotations around an existing detector. Current documentation moves ByteTrack into the separate trackers package. Pin compatible versions and verify model terms. |
| [FoundationVision ByteTrack](https://github.com/FoundationVision/ByteTrack) | Original MIT tracking implementation. Image-space association needs a separate geographic estimator. |
| [DSTL Stone Soup](https://github.com/dstl/Stone-Soup) | MIT framework for state estimation, tracking and missing observations. One simple estimator may suffice. |
| [OpenDrift](https://github.com/OpenDrift/opendrift) | GPL-2.0 ocean trajectory framework. Scientific dependencies and environmental inputs add setup work. Useful for precomputed scenarios. |
| [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) | Optional integration with compatible aircraft. Exact drone support and Pi server requirements must be checked. |
| [SeaDronesSee](https://github.com/Ben93kie/SeaDronesSee) | Maritime RGB detection/tracking benchmarks and evaluation tools. Single-object tracking clips keep the target visible, so separate loss/reacquisition tests are needed. |
| [MOBDrone evaluation](https://github.com/ciampluca/MOBDrone_eval) | Notebook and saved-prediction evaluation resources. Code license was not established in this review. |

The [PDMS research repository](https://github.com/DTU-IPL/pdms-man-overboard) currently exposes only a README promising a later code release. The [MAMMS dataset](https://zenodo.org/records/17979190) includes thermal UAV imagery and a geolocation subset, but access requires a user agreement and download link. Neither should gate a time-limited demo.

## Proposed opportunity and evaluation

The proposed contribution is a shared contact picture during intermittent drone-to-ship communications. Preserve observation time, receipt time, source identity, last evidence image and positional uncertainty. Represent visual loss independently from link loss. On reconnection, publish the freshest observation before buffered history. Novelty is a hypothesis requiring operator and competitor validation.

Evaluate one incident with a separate ground-truth trajectory. Compare the same observations and packet outages against a fixed last-seen-position baseline. Measure location error, observation age, recovery latency, transferred bytes, false associations, predicted-region area and empirical target coverage. Include a wrong-drift case so evaluation can expose a predictor that worsens the estimate.

The working scope and implementation decisions are recorded in the [open-ocean MOB proposal](../../01-ideas/open-ocean-mob-plan.md). Final requirements are being developed through the PRD interview.
