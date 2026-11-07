# Runtime implementation

This directory is reserved for the implementation selected through the PRD.

The proposed logical boundaries are capture/perception, localization/estimation, edge storage/transport, ship receiver and operator UI. Introduce modules when implementing these responsibilities. Keep device-specific code behind adapters and shared event semantics in one place.

A detector's confidence, track association and position uncertainty are separate values. Preserve this distinction at module boundaries. Add the chosen package layout and normal entry point with the first runnable increment.
