# Software and public repository shortlist

Research reviewed November 7, 2026. Runtime stack and dependency versions are pending the PRD and device bring-up. The following repositories are candidates with specific roles.

| Component | Candidate | Use and constraint |
| --- | --- | --- |
| Pi inference | [Hailo Pi examples](https://github.com/hailo-ai/hailo-rpi5-examples) | Run the supplied-image-compatible example first if the accelerator matches. Generic person detection has unmeasured swimmer performance. |
| Tracking | [Roboflow Trackers](https://github.com/roboflow/trackers) | Associate detections from the chosen model. Verify current API and pinned license. |
| Video annotations | [Supervision](https://github.com/roboflow/supervision) | MIT tools for processing and annotating detection results. |
| Tracking reference | [FoundationVision ByteTrack](https://github.com/FoundationVision/ByteTrack) | MIT original implementation. Benchmark GPU performance does not establish Pi speed. |
| Estimation | [DSTL Stone Soup](https://github.com/dstl/Stone-Soup) | MIT framework for tracking, state estimation and missing measurements. Start with a single relevant example. |
| Drift scenarios | [OpenDrift](https://github.com/OpenDrift/opendrift) | GPL-2.0 framework with Leeway SAR model. Dedicated environment and forcing data add work. Consider precomputing scenarios. |
| Aircraft interface | [MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) | Optional adapter for compatible aircraft. A Pi may require a separately running mavsdk_server. |
| Maritime benchmark | [SeaDronesSee](https://github.com/Ben93kie/SeaDronesSee) | RGB video, evaluation kits and model samples. Single-object clips retain visible targets, so add interruption scenarios. |
| Detection evaluation | [MOBDrone_eval](https://github.com/ciampluca/MOBDrone_eval) | Notebook using saved predictions and dataset images. Code-license status needs confirmation. |

## Version and access findings

Current [Supervision documentation](https://supervision.roboflow.com/latest/how_to/track_objects/) states that sv.ByteTrack was removed in 0.31.0 and demonstrates ByteTrackTracker from the separate trackers package. Pin compatible dependencies instead of mixing old examples with latest packages.

The old [Hailo apps infrastructure](https://github.com/hailo-ai/hailo-apps-infra) URL redirects to hailo-apps. Match the installed accelerator runtime and examples.

The [PDMS MOB repository](https://github.com/DTU-IPL/pdms-man-overboard) currently contains only a README promising a later release. The [MAMMS dataset](https://zenodo.org/records/17979190) offers thermal imagery and a geolocation subset but requires an access agreement and download link.

## Proposed first implementation

Python is a practical candidate for capture, adapters, storage and estimation, with a small local browser interface. Confirm the stack before adding manifests. Start with observation producer, receiver and display. Add a single camera adapter once its standalone example works.

Store events locally using an implementation appropriate to the chosen stack. Keep perception, world-coordinate estimation and transmission independently testable. Pin selected libraries and model artifacts. Cache dependencies and required assets for the event demonstration.

Record upstream URL, commit/release, code license, model/data license, target platform, install command and smoke-test result for each adopted dependency. Source review has been performed; local installation and compatibility testing remain pending.
