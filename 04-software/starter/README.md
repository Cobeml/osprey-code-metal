# Disaster response hackathon starter

Mission: help locate people, detect hazards, and get critical information to responders when infrastructure goes down.

This is a local, framework-neutral starter subtree within the whole hackathon workspace repository. It contains no application, device drivers, installed dependencies or deployment configuration. Architecture and hardware choices remain open.

## Layout

| Path | Purpose |
|---|---|
| `src/` | Application code and hardware adapters |
| `firmware/` | Microcontroller sketches or firmware, once the board is known |
| `tests/` | Meaningful tests when implementation exists |
| `scripts/` | Explicit setup, run or verification helpers |
| `docs/architecture.md` | Starting boundaries and deferred decisions |
| `examples/event.example.json` | Clearly simulated observation for discussing the data contract |

Preparation guides, equipment inventory, original PDF and this starter share the enclosing hackathon workspace repository. Since November 3, `git rev-parse --show-toplevel` resolves to `/Users/dexter/Projects/code-metal-hackathon`; this folder no longer has an independent `.git`. Keep code in this subtree; separate sharing or extraction would require its own decision.

## First commands

Run these inside this folder:

```sh
git rev-parse --show-toplevel
git status --short
git branch --show-current
python3 -m json.tool examples/event.example.json
```

Python is only used above as a convenient JSON validator; it does not select an implementation language. There is no build or test command until the team chooses a stack.

When implementation begins, record the exact board, firmware, OS, libraries and model versions in `docs/architecture.md`. Add setup/run/check commands to this README, then implement the smallest useful end-to-end path. Keep simulation and physical-hardware results distinguishable.

## Working with Git

Review `git diff` before committing. Git author identity must be set by the contributor if none is configured. The enclosing workspace is connected to the private `colt11044/code-metal-hackathon` repository; this subtree does not have a separate remote.

The starter-local `.gitignore` excludes common credentials, virtual environments, build outputs and generated observations within this subtree; it does not cover unrelated files elsewhere in the workspace. It cannot identify every secret: inspect staged changes before committing. An intentionally named `.env.example` may contain placeholders only.

## Example observation

The sample is a simulated temperature observation, not a hazard alarm or real measurement. Unknown location is represented by null coordinates and null uncertainty; it must not be interpreted as zero uncertainty. See `docs/architecture.md` before adopting this draft contract.

No project license has been selected. Choose one before sharing the code publicly, and retain third-party notices for any dependencies, models or datasets incorporated later.
