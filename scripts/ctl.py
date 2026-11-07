#!/usr/bin/env python3
"""Tiny control client. Usage:
  scripts/ctl.py state                      # phase, nodes, candidates
  scripts/ctl.py demo_start                 # any command; args as key=value
  scripts/ctl.py confirm                    # confirms the best candidate if no candidate_id given
  scripts/ctl.py set_rail rail_m=1.62
Base URL: $OSPREY_URL (default http://169.254.50.2:8000)
"""
import json
import os
import sys
import urllib.request
import uuid

BASE = os.environ.get("OSPREY_URL", "http://169.254.50.2:8000")


def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=5))


def post(cmd, args):
    body = json.dumps({"command_id": f"{cmd}-{uuid.uuid4().hex[:8]}", "cmd": cmd, "args": args}).encode()
    req = urllib.request.Request(BASE + "/api/commands", body, {"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=5))


def val(v):
    for f in (int, float):
        try:
            return f(v)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(v.lower(), v)


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "state":
        s = get("/api/state")
        print("phase", s["phase"], "| incident", (s["incident"] or {}).get("incident_id"))
        for n, v in s["nodes"].items():
            print(f"  {n:4} {v['pill']:12} src={v['source']:6} fps={v['fps']} cands={[c['candidate_id'] for c in v['candidates']]}")
        if s.get("drift"):
            print("  drift", s["drift"]["seed_kind"], f"{s['drift']['area90_m2']:.0f} m2", s["drift"]["forcing"])
        return
    cmd = sys.argv[1]
    args = dict(a.split("=", 1) for a in sys.argv[2:])
    args = {k: val(v) for k, v in args.items()}
    if cmd in ("confirm", "reject") and "candidate_id" not in args:
        s = get("/api/state")
        cs = sorted((c for v in s["nodes"].values() for c in v["candidates"]), key=lambda c: -c["confidence"])
        if not cs:
            sys.exit("no candidate")
        args["candidate_id"] = cs[0]["candidate_id"]
    print(post(cmd, args))


if __name__ == "__main__":
    main()
