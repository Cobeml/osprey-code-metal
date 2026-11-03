# Starting architecture notes

Status: generic scaffold, 2026-10-29. No product or hardware integration has been implemented.

## Confirmed context

The hackathon mission is to locate people, detect hazards and deliver critical information to responders when infrastructure fails. The equipment brief promises a Raspberry Pi 5 with a 26-TOPS accelerator, an Arduino-compatible board and Grove kit; exact device models and supplied software images still need confirmation. The broader equipment library is shared.

## Proposed boundaries

These are starting suggestions, not implementation decisions:

1. **Device adapter:** read one source and preserve its raw units, device identity, timestamp and error state.
2. **Observation record:** distinguish a measurement or detection from an interpreted hazard or responder decision.
3. **Local store:** retain observations when connectivity fails; handle duplicate IDs and stale data explicitly.
4. **Transport adapter:** carry compact records over the selected link without assuming Internet service.
5. **Responder view:** show provenance, age, unknown location and uncertainty; provide a human confirmation path.

Firmware should handle bounded sensor/actuator behavior and safe timeout behavior where applicable. High-level interpretation and user interface code can remain separate. Keep vendor SDK details inside adapters where practical.

## Draft observation example

`examples/event.example.json` is illustrative JSON, not a formal validated schema.

| Field | Proposed meaning |
|---|---|
| `schema_version` | Version of this draft record format |
| `id` | Stable identifier for deduplication; example uses a simulated ID |
| `observed_at` | UTC time the observation represents; not transport receipt time |
| `source` | Device identifier and origin adapter |
| `type` | Observation kind; this example is temperature, not hazard classification |
| `measurement` | Numeric value and explicit unit |
| `location` | Coordinates and accuracy information; unknowns remain null |
| `simulated` | Required explicit marker for synthetic/replayed demonstration data |

A physical location model still needs a coordinate frame, location provenance and an uncertainty convention. The example has none and uses null coordinates, frame and uncertainty. If using geographic coordinates, document latitude/longitude order and datum. If using local coordinates, document origin and axes. Do not replace an unknown location with the sensor's location unless the record semantics clearly say whose position it represents.

Confidence is omitted: there is no model prediction or calibrated probability in this example. Sensor accuracy and model confidence are different concepts. Add either only with a defined meaning and evidence.

## Decisions deferred

- Which responder problem and user interaction to demonstrate.
- Exact sensor/board/accelerator SKUs, voltage levels, interfaces and drivers.
- Laptop and target OS versions, language, framework and dependency lockfiles.
- Local storage format and network protocol; acknowledgement/retry behavior.
- Data retention, access control and handling of any real location or image data.
- Formal event schema, validation rules and timestamp synchronization.
- Measurement calibration, hazard thresholds and operator review behavior.
- Public repository host, license and deployment destination.

## Validation to add with implementation

Start with one adapter-to-view path. Record whether each test uses synthetic data, recorded data or a physical device. Check unplug/reconnect, process restart, stale observations, duplicates and operation without Internet where relevant. A passing simulation does not establish hardware performance or emergency-use reliability.
