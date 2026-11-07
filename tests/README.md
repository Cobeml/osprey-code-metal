# Automated verification

Add tests as executable behavior is implemented. Use the cases in [verification](../docs/engineering/verification.md) to trace tests to requirements.

Prioritize deterministic time advancement, dropped/duplicate/reordered messages, restarted sources, missing pose, visual loss while the link is healthy, and reconnect behavior. Hardware smoke tests should report exact device/software versions and remain distinguishable from replay tests.

Use shared inputs from fixtures. Keep recorded outputs in ignored artifacts directories. No executable tests exist yet.
