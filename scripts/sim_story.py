#!/usr/bin/env python3
"""Drive the fully simulated story through the REST API and check each phase.

Usage: python3 scripts/sim_story.py [http://169.254.50.2:8000]
Needs all three nodes on their sim sources. Prints a timing table.
"""
import json
import sys
import time
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def cmd(c, **args):
    body = json.dumps({"command_id": f"{c}-{uuid.uuid4().hex[:8]}", "cmd": c, "args": args}).encode()
    req = urllib.request.Request(BASE + "/api/commands", body, {"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=5))


def state():
    return json.load(urllib.request.urlopen(BASE + "/api/state", timeout=5))


def wait(pred, timeout, what):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = state()
        if pred(s):
            return s, time.time() - t0
        time.sleep(0.1)
    raise SystemExit(f"FAIL waiting for {what}; phase={state()['phase']}")


def cands(s):
    return [c for n in s["nodes"].values() for c in n["candidates"]]


def main():
    rows = []
    s = state()
    if s["incident"] and not s["incident"]["ended"]:
        cmd("end_incident")
        time.sleep(0.5)
    print(cmd("demo_start")["message"])
    s, dt = wait(lambda s: s["phase"] == "OVERBOARD", 10, "auto MOB")
    rows.append(("auto MOB after walk starts", dt, s["incident"]["detail"].get("reason")))
    s, dt = wait(lambda s: s["drift"] is not None, 3, "drift from overboard point")
    rows.append(("drift area shown", dt, s["drift"]["seed_kind"]))
    s, dt = wait(lambda s: cands(s), 15, "first candidate")
    rows.append(("first scout candidate", dt, cands(s)[0]["node_id"]))
    a = cmd("confirm", candidate_id=cands(s)[0]["candidate_id"])
    s, dt = wait(lambda s: s["phase"] == "TRACKING", 3, "tracking")
    rows.append(("confirm -> TRACKING", dt, a["message"]))
    s, dt = wait(lambda s: all(s["nodes"][n]["has_target"] for n in ("A", "B")), 15, "second scout auto-associates")
    rows.append(("second scout auto-associated", dt, "<= 50 m rule"))
    cmd("demo_hide", hidden=True)
    s, dt = wait(lambda s: s["phase"] == "CONTACT_LOST" and s["drift"], 12, "contact lost + drift")
    a0 = s["drift"]["area90_m2"]
    rows.append(("hide -> CONTACT LOST with drift", dt, f"90% area {a0:.0f} m2"))
    time.sleep(3)
    a1 = state()["drift"]["area90_m2"]
    rows.append(("drift area grows (3 s later)", 3.0, f"{a0:.0f} -> {a1:.0f} m2"))
    assert a1 > a0, "drift area did not grow"
    cmd("demo_inject", dist_m=30)
    s, dt = wait(lambda s: s["phase"] == "TRACKING", 8, "auto reacquire at 30 m")
    rows.append(("reappear 30 m -> auto resume", dt, "no confirm needed"))
    cmd("demo_hide", hidden=True)
    wait(lambda s: s["phase"] == "CONTACT_LOST", 12, "contact lost again")
    cmd("demo_inject", dist_m=80)
    s, dt = wait(lambda s: s["phase"] == "CANDIDATE", 8, "80 m candidate")
    rows.append(("reappear 80 m -> CANDIDATE", dt, cands(s)[0]["reason"]))
    cmd("confirm", candidate_id=cands(s)[0]["candidate_id"])
    wait(lambda s: s["phase"] == "TRACKING", 3, "tracking after confirm")
    a = cmd("end_incident")
    s, dt = wait(lambda s: s["phase"] == "ENDED", 3, "ended")
    rows.append(("END INCIDENT", dt, a["message"]))
    print(f"\n{'step':38} {'secs':>6}  detail")
    for name, dt, detail in rows:
        print(f"{name:38} {dt:6.2f}  {detail}")
    print("\nPASS: simulated story completed")


if __name__ == "__main__":
    main()
