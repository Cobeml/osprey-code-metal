# Man overboard response plan

November 7, 2026 at 11:26 AM EST. Curated, paraphrased team notes based on the complete three-part transcript. [Original Granola meeting](https://notes.granola.ai/d/d8470afa-fe9b-4ce5-a3cc-e39d5fc32f79)

## Intent discussed

Reduce the interval from a person entering the water to useful awareness of their location, then maintain contact through rescue. The team explored drones rapidly acquiring a person, maintaining observation and broadcasting a position.

Participants considered whether the main product should focus on recognition and tracking, a common operating picture, search behavior, or communications. The final slice remained unresolved.

## Initial scope and ideas

- Treat detection of the fall as a separate problem. Begin from a declared incident.
- Consider a drone-visible signal or beacon to help rescuers identify its location.
- Use drift prediction to inform the search before acquisition.
- Explore multiple drones coordinating as they deploy.
- Prioritize a visible, complete demonstration under the available equipment and time constraints.

## Communications proposal

The drone may retain visual contact while the ship temporarily loses its data link. Participants suggested sending updates roughly every three seconds containing position, a captured image and visual-contact status. During a gap, retain the last datum and let uncertainty grow. Preserve evidence if the drone becomes unavailable because of power or weather.

Limited bandwidth matters even when the link is connected. The group considered the communications-contingency layer a useful addition to the acquisition demonstration.

## Unresolved questions

What exactly must be built during the event? Does lock mean an image track, camera pointing or aircraft following? What can the hardware reliably demonstrate? How much of the initial search, coordination and recovery should be required?

## Engineering interpretation

The discussion's estimate that lock-on and broadcast could address about 90% of scenarios is unvalidated speculation. A thermal camera and a night-vision-visible IR strobe may use different spectral bands; compatibility must be checked. A radio outage leaves the ship's current knowledge of remote visual status unknown, even if the remote node continues tracking.
