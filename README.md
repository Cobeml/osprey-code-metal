# Team 29 — Maritime search and rescue

Primary repository as of November 7, 2026 is [CodeMetalForge-Hackathon/Team-29](https://github.com/CodeMetalForge-Hackathon/Team-29). Continue project work in this checkout.

Start with the [project index](INDEX.md), [open-ocean MOB proposal](01-ideas/open-ocean-mob-plan.md), and [mission requirements](01-ideas/forge-2026-mission-brief.md). PRD discovery is underway, with one question at a time. The primary operator and final demo scope remain open decisions.

The repository includes preparation history, research, the starter scaffold and [interactive concept mockups](05-prototypes/README.md). The application and hardware integration are still to be built. The preparation material below preserves historical context and may describe earlier locations or repository state.

The existing Team-29 LICENSE is the repository's license. Third-party code, data, and basemaps retain their own terms.

---
# Disaster response hackathon

Saved 2026-10-29. The event is **next week**, as described by Colton; its exact date and location are not yet recorded.

> The mission: help locate people, detect hazards, and get critical information to responders when infrastructure goes down. Start thinking about what you could build—and what could make a difference when every second counts.

Start with a small system that reads one sensor, stores an observation, and shows it to a responder without Internet. The guaranteed kit supports that direction. Cameras, specialist radios and robots are shared equipment, so make them extensions until their availability and exact models are known.

## Read in this order

1. [Equipment guide](02-equipment/equipment-guide.md): what every listed item does and where it connects.
2. [Three-hour crash course](02-equipment/crash-course.md): the concepts and one complete data path.
3. [Software preparation list](04-software/preparation-list.md): essential, conditional and deferred tools, with upstream links.
4. [Preflight checklist](04-software/preflight-checklist.md): what to prepare, test and ask before arrival.
5. [Man-overboard research](03-research/reports/man-overboard-systems.md) covers existing systems, public repositories and prototype feasibility.
6. [Research synthesis](03-research/reports/Disaster%20response%20hardware%20readiness.md): the main technical decisions and supporting evidence.

[INDEX.md](INDEX.md) links every deliverable and the underlying research. The [mission requirements](01-ideas/forge-2026-mission-brief.md) preserve the organizer briefing.

## Folder map

| Folder | Contents |
|---|---|
| `01-ideas/` | Mission, confirmed context and proposed projects |
| `02-equipment/` | Equipment guide, crash course, original PDF and extracted text |
| `03-research/` | Cited synthesis and supporting research notes |
| `04-software/` | Prioritized preparation, preflight and starter code within the workspace repository |

## Current state

The original PDF is saved and its copy verified byte-for-byte. Research uses official project and manufacturer sources checked on 2026-10-29. Mac preparation is the working assumption; the laptop being brought has not been confirmed. The Raspberry Pi and other Linux targets have separate setup requirements.

November 3: the existing unborn `main` Git repository was promoted from `04-software/starter/.git` to the workspace root `/Users/dexter/Projects/code-metal-hackathon/.git`. The whole workspace now shares one repository; all eight original starter files and Git configuration were preserved. No files were staged, no commit was created and no remote was added. See [the verified boundary-conversion receipt](../../OS/checks/backups/hackathon-repo-boundary-2026-11-03/receipt.json). The [starter](04-software/starter/README.md) still contains a simulated event example and neutral code/firmware folders, with no application or installed dependencies. Its nested ignore rules apply to that subtree, not automatically to the entire workspace. The parent OS repository was not staged or committed.

No software installation, hardware integration, performance measurement or emergency-use validation has been performed. Preparation recommendations and project ideas are proposals; no idea or implementation stack has been selected.

## Standalone repository migration — November 3, 2026

The workspace root is the single Git boundary, including the preserved eight starter files. The private GitHub destination is `colt11044/code-metal-hackathon`. Local `.codex/`, `.mcp.json`, and `CLAUDE.md` remain untracked. The earlier no-commit/no-remote paragraph above is the dated boundary-conversion receipt. No executable application or hardware validation is implied by publication.
